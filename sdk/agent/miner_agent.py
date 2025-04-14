# File mới: sdk/agent/miner_agent.py

import asyncio
import logging
import time
import httpx
from typing import Optional, Dict, Tuple, List

# Import từ SDK
from sdk.config.settings import Settings
from sdk.core.datatypes import MinerConsensusResult, CycleConsensusResults
from sdk.metagraph.metagraph_data import MinerDatum
from sdk.formulas import update_trust_score
from sdk.metagraph.hash.hash_datum import hash_data
from sdk.keymanager.decryption_utils import decode_hotkey_skey
from sdk.service.context import get_chain_context
from sdk.service.utxos import get_utxo_from_str
from sdk.smartcontract.validator import read_validator  # Để lấy script hash/bytes
from pycardano import (
    BlockFrostChainContext,
    Network,
    ExtendedSigningKey,
    Address,
    UTxO,
    PlutusData,
    Redeemer,
    ScriptHash,
    TransactionBuilder,
    TransactionOutput,
    Value,
    TransactionId,
    PaymentSigningKey,
    StakeSigningKey,
    PlutusV3Script,  # Import đầy đủ
    SigningKey,
)

logger = logging.getLogger(__name__)

# --- Giả định Redeemer Tag cho Miner Self-Update ---
# Cần khớp với định nghĩa trong Plutus Script sau này
MINER_SELF_UPDATE_REDEEMER_TAG = 1
# ---------------------------------------------------


class MinerAgent:
    """
    Logic cho Miner để tự động lấy kết quả đồng thuận và cập nhật trạng thái on-chain.
    """

    def __init__(
        self,
        miner_uid_hex: bytes,
        config: Settings,
        miner_skey: ExtendedSigningKey,
        miner_stake_skey: Optional[ExtendedSigningKey] = None,
    ):
        self.miner_uid_hex = miner_uid_hex
        self.miner_uid_bytes = miner_uid_hex
        self.config = config
        self.signing_key = miner_skey
        self.stake_signing_key = miner_stake_skey
        self.network = Network.TESTNET

        # Tạo context và http client riêng cho miner agent
        self.context = get_chain_context(
            method="blockfrost"
        )  # Dùng config của miner nếu khác validator
        if not self.context:
            raise RuntimeError("MinerAgent: Failed to initialize Cardano context.")

        self.http_client = httpx.AsyncClient(timeout=15.0)  # Timeout riêng

        # Load script details
        try:
            validator_details = read_validator()
            self.script_hash: ScriptHash = validator_details["script_hash"]  # type: ignore
            self.script_bytes: PlutusV3Script = validator_details["script_bytes"]  # type: ignore
            self.contract_address = Address(
                payment_part=self.script_hash, network=self.network
            )
        except Exception as e:
            raise RuntimeError(f"MinerAgent: Failed to load script details: {e}") from e

        # Địa chỉ ví cá nhân của miner (dùng để trả phí/collateral)
        pay_vkey = self.signing_key.to_verification_key()
        stake_vkey = (
            self.stake_signing_key.to_verification_key()
            if self.stake_signing_key
            else None
        )
        self.miner_wallet_address = Address(
            payment_part=pay_vkey.hash(),
            staking_part=stake_vkey.hash() if stake_vkey else None,
            network=self.network,
        )

        self.last_processed_cycle = -1  # Theo dõi chu kỳ đã xử lý
        self.last_known_utxo: Optional[UTxO] = None  # Cache UTXO cuối cùng

        logger.info(f"MinerAgent initialized for Miner UID: {self.miner_uid_hex}")
        logger.info(f" - Wallet Address: {self.miner_wallet_address}")
        logger.info(f" - Contract Address: {self.contract_address}")

    async def fetch_consensus_result(
        self, cycle_num: int, validator_api_url: str
    ) -> Optional[MinerConsensusResult]:
        """Lấy kết quả đồng thuận cho miner từ API validator."""
        target_url = f"{validator_api_url.rstrip('/')}/v1/consensus/results/{cycle_num}"
        logger.debug(
            f"Miner {self.miner_uid_hex}: Fetching results for cycle {cycle_num} from {target_url}"
        )
        try:
            response = await self.http_client.get(target_url, timeout=10.0)
            response.raise_for_status()  # Check for 4xx/5xx errors
            data = response.json()
            cycle_results = CycleConsensusResults(**data)  # Validate response structure

            if cycle_results.cycle != cycle_num:
                logger.warning(
                    f"Fetched results for wrong cycle ({cycle_results.cycle}) when requesting {cycle_num}"
                )
                return None

            # Tìm kết quả của chính miner này
            miner_result_data = cycle_results.results.get(self.miner_uid_hex)
            if miner_result_data:
                logger.info(
                    f"Miner {self.miner_uid_hex}: Successfully fetched consensus result for cycle {cycle_num}"
                )
                # Trả về đối tượng MinerConsensusResult đã được Pydantic parse
                return miner_result_data
            else:
                logger.warning(
                    f"Miner {self.miner_uid_hex}: Result not found for self in cycle {cycle_num} data."
                )
                return None

        except httpx.RequestError as e:
            logger.error(
                f"Miner {self.miner_uid_hex}: Network error fetching results for cycle {cycle_num}: {e}"
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Miner {self.miner_uid_hex}: HTTP error fetching results for cycle {cycle_num}: Status {e.response.status_code}"
            )
            return None
        except Exception as e:  # Includes JSONDecodeError, Pydantic ValidationError
            logger.exception(
                f"Miner {self.miner_uid_hex}: Error processing results for cycle {cycle_num}: {e}"
            )
            return None

    async def find_own_utxo(self) -> Optional[UTxO]:
        """Tìm UTXO chứa MinerDatum của miner này trên blockchain."""
        logger.debug(
            f"Miner {self.miner_uid_hex}: Searching for own Datum UTxO at {self.contract_address}..."
        )
        try:
            utxo = get_utxo_from_str(  # Hàm này cần trả về UTXO object
                contract_address=self.contract_address,
                datumclass=MinerDatum,
                context=self.context,
                search_uid=self.miner_uid_bytes,
            )
            if utxo:
                logger.info(f"Miner {self.miner_uid_hex}: Found own UTxO: {utxo.input}")
                self.last_known_utxo = utxo  # Cache lại
            else:
                logger.warning(
                    f"Miner {self.miner_uid_hex}: Own Datum UTxO not found at {self.contract_address}."
                )
                self.last_known_utxo = None
            return utxo
        except Exception as e:
            logger.exception(f"Miner {self.miner_uid_hex}: Error finding own UTxO: {e}")
            return None

    def calculate_new_datum(
        self,
        old_datum: MinerDatum,
        consensus_result: MinerConsensusResult,
        current_cycle: int,
    ) -> Optional[MinerDatum]:
        """Tính toán và tạo MinerDatum mới."""
        logger.debug(
            f"Miner {self.miner_uid_hex}: Calculating new datum for cycle {current_cycle}..."
        )
        try:
            divisor = self.config.METAGRAPH_DATUM_INT_DIVISOR
            p_adj = consensus_result.p_adj
            incentive_float = consensus_result.calculated_incentive

            # Lấy trạng thái cũ
            trust_score_old = old_datum.trust_score  # Property đã unscale
            rewards_old = old_datum.accumulated_rewards  # Đây là int đã scale
            history_old = (
                []
            )  # TODO: Cần cơ chế decode history từ hash cũ nếu muốn giữ lại

            # Tính trust mới
            # Giả định time_since=1 vì miner đã được đánh giá
            new_trust_score_float = update_trust_score(
                trust_score_old=trust_score_old,
                time_since_last_eval=1,
                score_new=p_adj,  # score_new là P_adj
                # Lấy các tham số từ config của Miner Agent
                delta_trust=self.config.CONSENSUS_PARAM_DELTA_TRUST,
                alpha_base=self.config.CONSENSUS_PARAM_ALPHA_BASE,
                k_alpha=self.config.CONSENSUS_PARAM_K_ALPHA,
                update_sigmoid_L=self.config.CONSENSUS_PARAM_UPDATE_SIG_L,
                update_sigmoid_k=self.config.CONSENSUS_PARAM_UPDATE_SIG_K,
                update_sigmoid_x0=self.config.CONSENSUS_PARAM_UPDATE_SIG_X0,
            )

            # Tính reward mới
            rewards_new = rewards_old + int(incentive_float * divisor)

            # Tính hash history mới
            # TODO: Cần thêm logic cập nhật history thực tế
            new_history = history_old + [p_adj]  # Ví dụ đơn giản
            new_history = new_history[
                -self.config.CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN :
            ]
            new_perf_history_hash = (
                hash_data(new_history)
                if new_history
                else old_datum.performance_history_hash
            )

            # Tạo Datum mới
            new_datum = MinerDatum(
                uid=old_datum.uid,
                subnet_uid=old_datum.subnet_uid,
                stake=old_datum.stake,
                scaled_last_performance=int(p_adj * divisor),
                scaled_trust_score=int(new_trust_score_float * divisor),
                accumulated_rewards=rewards_new,
                last_update_slot=current_cycle,
                performance_history_hash=new_perf_history_hash,
                wallet_addr_hash=old_datum.wallet_addr_hash,  # Giữ nguyên hash ví
                status=old_datum.status,  # Giữ nguyên status (trừ khi có logic thay đổi)
                registration_slot=old_datum.registration_slot,
                api_endpoint=old_datum.api_endpoint,  # Giữ nguyên endpoint
            )
            logger.info(
                f"Miner {self.miner_uid_hex}: Calculated new MinerDatum: {new_datum}"
            )
            return new_datum

        except Exception as e:
            logger.exception(
                f"Miner {self.miner_uid_hex}: Error calculating new datum: {e}"
            )
            return None

    async def commit_self_update(
        self, old_utxo: UTxO, new_datum: MinerDatum
    ) -> Optional[str]:
        """Xây dựng, ký và gửi giao dịch tự cập nhật."""
        logger.info(f"Miner {self.miner_uid_hex}: Attempting to commit self-update...")
        try:
            builder = TransactionBuilder(context=self.context)

            # Input 1: UTXO Datum cũ
            # Redeemer = MinerSelfUpdate (Tag 1 - giả định)
            # Cần kiểm tra xem script yêu cầu data trong redeemer không
            self_update_redeemer = Redeemer(0)
            builder.add_script_input(
                utxo=old_utxo, script=self.script_bytes, redeemer=self_update_redeemer
            )
            logger.debug(f"Added script input: {old_utxo.input}")

            # Input 2: Từ ví cá nhân miner để trả phí/collateral
            # TransactionBuilder sẽ tự chọn UTXO từ địa chỉ này
            builder.add_input_address(self.miner_wallet_address)
            logger.debug(f"Added wallet input address: {self.miner_wallet_address}")

            # Output 1: Trả về contract với Datum mới và giữ nguyên giá trị
            output_value: Value = old_utxo.output.amount
            builder.add_output(
                TransactionOutput(
                    address=self.contract_address, amount=output_value, datum=new_datum
                )
            )
            logger.debug(
                f"Added script output with new datum. Amount: {output_value.coin}"
            )

            # Required Signer: Chính là miner (hash của payment key)
            pay_vkey = self.signing_key.to_verification_key()
            builder.required_signers = [pay_vkey.hash()]  # type: ignore
            logger.debug(f"Set required signer: {pay_vkey.hash().to_primitive().hex()}")  # type: ignore

            # Build, Sign (chỉ bằng khóa của miner), Submit
            logger.debug("Building and signing transaction...")
            # --- SỬA LỖI SIGNING KEYS ---
            # Cần truyền list chứa payment key của miner. Nếu script cần stake key, thêm stake_signing_key vào list.
            signing_keys_list: List[SigningKey | ExtendedSigningKey] = [self.signing_key]
            # Script 'always_true' hiện tại không kiểm tra stake key, nhưng nếu script sau này cần:
            # if self.stake_signing_key:
            #     stake_vkey = self.stake_signing_key.to_verification_key()
            #     if stake_vkey.hash() in builder.required_signers: # Kiểm tra nếu script yêu cầu
            #         signing_keys_list.append(self.stake_signing_key)

            signed_tx = builder.build_and_sign(
                signing_keys=signing_keys_list,  # Truyền list key
                change_address=self.miner_wallet_address,  # Địa chỉ nhận tiền thừa
            )
            # --- KẾT THÚC SỬA LỖI ---

            logger.info(
                f"Submitting self-update transaction (Fee: {signed_tx.transaction_body.fee})..."
            )
            tx_id: TransactionId = await self.context.submit_tx(signed_tx)  # type: ignore
            tx_id_str = str(tx_id)
            logger.info(
                f"Miner {self.miner_uid_hex}: Self-update submitted successfully! TxID: {tx_id_str}"
            )
            return tx_id_str

        # ... (Xử lý lỗi ApiError, Exception như trong commit_updates_logic) ...
        except Exception as e:
            logger.exception(
                f"Miner {self.miner_uid_hex}: Failed to commit self-update: {e}"
            )
            return None

    async def run(self, validator_api_url: str, check_interval_seconds: int = 60):
        """Vòng lặp chính của Miner Agent."""
        logger.info(f"MinerAgent for {self.miner_uid_hex} starting run loop...")
        while True:
            try:
                # Xác định chu kỳ cần kiểm tra (chu kỳ sau chu kỳ đã xử lý cuối cùng)
                target_cycle = self.last_processed_cycle + 1
                logger.debug(
                    f"Checking for consensus results of cycle {target_cycle}..."
                )

                # 1. Fetch kết quả
                consensus_result = await self.fetch_consensus_result(
                    target_cycle, validator_api_url
                )

                if consensus_result:
                    logger.info(
                        f"Found results for cycle {target_cycle}. Preparing update."
                    )

                    # 2. Tìm UTXO cũ
                    # Nên tìm lại UTXO mỗi lần để đảm bảo lấy trạng thái mới nhất
                    old_utxo = await self.find_own_utxo()
                    if not old_utxo or not old_utxo.output.datum:
                        logger.error(
                            f"Cannot proceed with update for cycle {target_cycle}: Own UTXO/Datum not found."
                        )
                        # Chờ và thử lại ở lần sau
                        await asyncio.sleep(check_interval_seconds)
                        continue

                    try:
                        old_datum = MinerDatum.from_cbor(old_utxo.output.datum.cbor)  # type: ignore
                    except Exception as dec_err:
                        logger.error(
                            f"Failed to decode current datum for UTxO {old_utxo.input}: {dec_err}"
                        )
                        await asyncio.sleep(check_interval_seconds)
                        continue

                    # 3. Tính Datum mới
                    new_datum = self.calculate_new_datum(
                        old_datum, consensus_result, target_cycle # type: ignore
                    )

                    if new_datum:
                        # 4. Commit
                        tx_id = await self.commit_self_update(old_utxo, new_datum)
                        if tx_id:
                            logger.info(
                                f"Successfully processed and committed update for cycle {target_cycle}."
                            )
                            self.last_processed_cycle = (
                                target_cycle  # Cập nhật chu kỳ đã xử lý
                            )
                            # Có thể chờ một chút trước khi kiểm tra chu kỳ tiếp theo
                            await asyncio.sleep(10)
                        else:
                            logger.error(
                                f"Commit failed for cycle {target_cycle}. Will retry later."
                            )
                            # Không tăng last_processed_cycle để thử lại
                    else:
                        logger.error(
                            f"Failed to calculate new datum for cycle {target_cycle}. Skipping commit."
                        )
                        # Có thể muốn tăng last_processed_cycle để bỏ qua chu kỳ lỗi này? Tạm thời không.

                else:
                    # Chưa có kết quả cho chu kỳ target_cycle
                    logger.debug(f"No results found for cycle {target_cycle} yet.")

            except Exception as loop_err:
                logger.exception(f"Error in MinerAgent run loop: {loop_err}")

            # Chờ trước khi kiểm tra lại
            logger.debug(f"Waiting {check_interval_seconds}s before next check...")
            await asyncio.sleep(check_interval_seconds)

    async def close(self):
        """Đóng các tài nguyên (ví dụ: http client)."""
        await self.http_client.aclose()
        logger.info(f"MinerAgent for {self.miner_uid_hex} closed HTTP client.")
