# File: sdk/agent/miner_agent.py
# Logic cho Miner để tự động lấy kết quả đồng thuận và cập nhật trạng thái on-chain.

import asyncio
import logging
import time
import httpx
import binascii  # <<<--- Import binascii
from typing import Optional, Dict, Tuple, List

# Import từ SDK
from sdk.config.settings import Settings
from sdk.core.datatypes import MinerConsensusResult, CycleConsensusResults

# Import lớp Datum và các công thức cần thiết
from sdk.metagraph.metagraph_datum import MinerDatum  # <<<--- Chỉ cần MinerDatum
from sdk.formulas import update_trust_score  # Import hàm cập nhật trust
from sdk.metagraph.hash.hash_datum import hash_data

# Import các tiện ích tương tác Cardano
from sdk.keymanager.decryption_utils import decode_hotkey_skey
from sdk.service.context import get_chain_context
from sdk.service.utxos import get_utxo_from_str  # Hàm tìm UTXO theo UID
from sdk.smartcontract.validator import read_validator  # Để lấy script hash/bytes

# Import các kiểu PyCardano
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
    PlutusV3Script,
    SigningKey,  # Import SigningKey nếu dùng trong build_and_sign
)

# Lấy logger đã cấu hình
logger = logging.getLogger(__name__)

# --- Giả định Redeemer Tag cho Miner Self-Update ---
# Cần khớp với định nghĩa trong Plutus Script
MINER_SELF_UPDATE_REDEEMER_TAG = 1  # Ví dụ: Tag 1 cho hành động miner tự cập nhật
# ---------------------------------------------------


class MinerAgent:
    """
    Agent chạy song song với Miner Server, chịu trách nhiệm:
    1. Fetch kết quả đồng thuận từ Validator API.
    2. Tìm UTXO Datum của chính mình trên blockchain.
    3. Tính toán trạng thái Datum mới (trust, reward, performance...).
    4. Gửi giao dịch self-update lên Cardano để cập nhật Datum.
    """

    def __init__(
        self,
        miner_uid_hex: str,  # <<<--- Nhận UID hex dạng string từ cấu hình
        config: Settings,
        miner_skey: ExtendedSigningKey,  # Khóa ký payment chính
        miner_stake_skey: Optional[ExtendedSigningKey] = None,  # Khóa ký stake (nếu có)
    ):
        """
        Khởi tạo Miner Agent.

        Args:
            miner_uid_hex: UID hex *on-chain* của miner này (dạng string).
            config: Đối tượng Settings chứa các tham số cấu hình.
            miner_skey: Khóa ký payment (ExtendedSigningKey) của ví miner.
            miner_stake_skey: Khóa ký stake (ExtendedSigningKey) của ví miner (tùy chọn).

        Raises:
            ValueError: Nếu miner_uid_hex không hợp lệ.
            RuntimeError: Nếu không thể khởi tạo context Cardano hoặc load script.
        """
        if not miner_uid_hex or not isinstance(miner_uid_hex, str):
            raise ValueError("MinerAgent requires a valid miner_uid_hex (string).")

        self.miner_uid_hex: str = miner_uid_hex
        try:
            # Chuyển đổi và lưu trữ UID dạng bytes
            self.miner_uid_bytes: bytes = binascii.unhexlify(miner_uid_hex)
        except (binascii.Error, TypeError) as e:
            raise ValueError(
                f"Invalid miner_uid_hex format: {miner_uid_hex}. Error: {e}"
            ) from e

        self.config = config
        self.signing_key = miner_skey
        self.stake_signing_key = miner_stake_skey

        # --- Khởi tạo Context và Network ---
        try:
            self.context = get_chain_context(method="blockfrost")
            if not self.context:
                raise RuntimeError("Failed to initialize Cardano context.")
            self.network = self.context.network  # Lấy network từ context
        except Exception as e:
            logger.exception("Failed to initialize Cardano context for MinerAgent.")
            raise RuntimeError(f"Failed to initialize Cardano context: {e}") from e
        # ------------------------------------

        # HTTP client để gọi API Validator
        self.http_client = httpx.AsyncClient(timeout=15.0)

        # --- Load Script Details ---
        try:
            validator_details = read_validator()
            if (
                not validator_details
                or "script_hash" not in validator_details
                or "script_bytes" not in validator_details
            ):
                raise ValueError("Invalid script details loaded.")
            self.script_hash: ScriptHash = validator_details["script_hash"]
            self.script_bytes: PlutusV3Script = validator_details["script_bytes"]
            self.contract_address = Address(
                payment_part=self.script_hash, network=self.network
            )
        except Exception as e:
            logger.exception("Failed to load script details for MinerAgent.")
            raise RuntimeError(f"Failed to load script details: {e}") from e
        # ---------------------------

        # --- Tạo Địa chỉ Ví Miner ---
        try:
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
        except Exception as e:
            logger.exception("Failed to derive miner wallet address.")
            raise RuntimeError(f"Failed to derive miner wallet address: {e}") from e
        # ---------------------------

        # State theo dõi
        self.last_processed_cycle = -1
        self.last_known_utxo: Optional[UTxO] = None  # Cache UTXO tìm được gần nhất

        logger.info(f"MinerAgent initialized for Miner UID: {self.miner_uid_hex}")
        logger.info(f" - Wallet Address: {self.miner_wallet_address}")
        logger.info(f" - Contract Address: {self.contract_address}")
        logger.info(f" - UID Bytes Used for Search: {self.miner_uid_bytes.hex()}")

    async def fetch_consensus_result(
        self, cycle_num: int, validator_api_url: str
    ) -> Optional[MinerConsensusResult]:
        """Lấy kết quả đồng thuận cho miner từ API validator cho một chu kỳ cụ thể."""
        # Endpoint API cần khớp với định nghĩa trong API của validator
        target_url = f"{validator_api_url.rstrip('/')}/v1/consensus/results/{cycle_num}"
        logger.debug(
            f"Miner {self.miner_uid_hex}: Fetching results for cycle {cycle_num} from {target_url}"
        )
        try:
            response = await self.http_client.get(target_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            # Validate cấu trúc response bằng Pydantic model
            cycle_results = CycleConsensusResults(**data)

            if cycle_results.cycle != cycle_num:
                logger.warning(
                    f"Fetched results for wrong cycle ({cycle_results.cycle}) when requesting {cycle_num}"
                )
                return None

            # Tìm kết quả của chính miner này trong dict `results` bằng UID hex
            miner_result_data = cycle_results.results.get(self.miner_uid_hex)
            if miner_result_data:
                logger.info(
                    f"Miner {self.miner_uid_hex}: Successfully fetched consensus result for cycle {cycle_num}"
                )
                return miner_result_data  # Trả về đối tượng MinerConsensusResult
            else:
                logger.info(
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
            # Có thể log response body để debug: logger.error(f"Response body: {e.response.text[:500]}")
            return None
        except Exception as e:  # Bao gồm lỗi JSONDecodeError, Pydantic ValidationError
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
            # Sử dụng UID bytes đã được decode để tìm kiếm
            utxo = await asyncio.to_thread(
                get_utxo_from_str,  # get_utxo_from_str là hàm đồng bộ
                contract_address=self.contract_address,
                datumclass=MinerDatum,
                context=self.context,
                search_uid=self.miner_uid_bytes,  # <<<--- Dùng UID bytes
            )
            if utxo:
                logger.info(f"Miner {self.miner_uid_hex}: Found own UTxO: {utxo.input}")
                self.last_known_utxo = utxo
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
        """
        Tính toán và tạo MinerDatum mới dựa trên trạng thái cũ và kết quả đồng thuận.
        """
        logger.debug(
            f"Miner {self.miner_uid_hex}: Calculating new datum for cycle {current_cycle}..."
        )
        try:
            divisor = self.config.METAGRAPH_DATUM_INT_DIVISOR
            p_adj = consensus_result.p_adj
            incentive_float = consensus_result.calculated_incentive

            # Lấy trạng thái cũ từ old_datum
            trust_score_old = old_datum.trust_score  # Property đã unscale
            rewards_old = old_datum.accumulated_rewards  # Đây là int đã scale
            # TODO: Cần cơ chế decode history từ hash cũ nếu muốn giữ lại và append
            history_old = []  # Tạm thời coi như bắt đầu lại history mỗi lần tính

            # --- Tính Trust Score mới ---
            # Giả định miner đã được đánh giá (time_since=1) vì có kết quả consensus
            new_trust_score_float = update_trust_score(
                trust_score_old=trust_score_old,
                time_since_last_eval=1,
                score_new=p_adj,  # Dùng P_adj từ kết quả consensus
                delta_trust=self.config.CONSENSUS_PARAM_DELTA_TRUST,
                alpha_base=self.config.CONSENSUS_PARAM_ALPHA_BASE,
                k_alpha=self.config.CONSENSUS_PARAM_K_ALPHA,
                update_sigmoid_L=self.config.CONSENSUS_PARAM_UPDATE_SIG_L,
                update_sigmoid_k=self.config.CONSENSUS_PARAM_UPDATE_SIG_K,
                update_sigmoid_x0=self.config.CONSENSUS_PARAM_UPDATE_SIG_X0,
            )
            # Đảm bảo trust score nằm trong khoảng [0, 1]
            new_trust_score_float = max(0.0, min(1.0, new_trust_score_float))

            # --- Tính Accumulated Rewards mới ---
            # Cộng dồn phần thưởng đã tính (incentive_float) vào reward cũ
            rewards_new = rewards_old + int(incentive_float * divisor)

            # --- Tính Performance History Hash mới ---
            # Thêm P_adj vào history (sau khi unscale?) -> Nên thêm P_adj (float)
            new_history = history_old + [p_adj]
            # Giữ lại độ dài tối đa theo cấu hình
            new_history = new_history[
                -self.config.CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN :
            ]
            # Hash lại list history mới
            new_perf_history_hash = (
                hash_data(new_history)
                if new_history
                else old_datum.performance_history_hash
            )

            # --- Tạo đối tượng MinerDatum mới ---
            # Giữ nguyên các trường không thay đổi từ old_datum
            new_datum = MinerDatum(
                uid=old_datum.uid,  # <<<--- Dùng UID bytes từ datum cũ
                subnet_uid=old_datum.subnet_uid,
                stake=old_datum.stake,  # Giữ nguyên stake (chưa có logic thay đổi stake ở đây)
                scaled_last_performance=int(
                    p_adj * divisor
                ),  # <<<--- Cập nhật performance mới
                scaled_trust_score=int(
                    new_trust_score_float * divisor
                ),  # <<<--- Cập nhật trust mới
                accumulated_rewards=rewards_new,  # <<<--- Cập nhật reward mới
                last_update_slot=current_cycle,  # <<<--- Cập nhật slot
                performance_history_hash=new_perf_history_hash,  # <<<--- Cập nhật hash history mới
                wallet_addr_hash=old_datum.wallet_addr_hash,  # Giữ nguyên hash ví bytes
                status=old_datum.status,  # Giữ nguyên status (trừ khi có logic thay đổi)
                registration_slot=old_datum.registration_slot,  # Giữ nguyên slot đăng ký
                api_endpoint=old_datum.api_endpoint,  # Giữ nguyên endpoint bytes
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
        """Xây dựng, ký và gửi giao dịch tự cập nhật MinerDatum lên blockchain."""
        logger.info(
            f"Miner {self.miner_uid_hex}: Attempting to commit self-update transaction..."
        )
        try:
            builder = TransactionBuilder(context=self.context)

            # --- Input 1: UTXO Datum cũ của miner ---
            # Redeemer cần khớp với định nghĩa trong Plutus script cho hành động self-update
            # Giả định tag là MINER_SELF_UPDATE_REDEEMER_TAG và không cần data phức tạp
            self_update_redeemer = Redeemer(0)  # Data = None
            builder.add_script_input(
                utxo=old_utxo,
                script=self.script_bytes,  # Script Plutus dùng chung
                redeemer=self_update_redeemer,
            )
            logger.debug(f"Added script input: {old_utxo.input}")

            # --- Input 2: Từ ví cá nhân của miner để trả phí ---
            # TransactionBuilder sẽ tự động chọn UTXO từ địa chỉ này
            builder.add_input_address(self.miner_wallet_address)
            logger.debug(f"Added wallet input address: {self.miner_wallet_address}")

            # --- Output 1: Trả về contract với Datum mới và giữ nguyên giá trị ---
            output_value: Value = (
                old_utxo.output.amount
            )  # Giữ nguyên value (ADA + tokens nếu có)
            builder.add_output(
                TransactionOutput(
                    address=self.contract_address,
                    amount=output_value,
                    datum=new_datum,  # <<<--- Datum mới đã tính toán
                )
            )
            logger.debug(
                f"Added script output with new datum. Amount: {output_value.coin} Lovelace"
            )

            # --- Required Signer: Chính là miner ---
            # Chữ ký được kiểm tra dựa trên hash của payment verification key
            pay_vkey = self.signing_key.to_verification_key()
            builder.required_signers = [pay_vkey.hash()]  # type: ignore
            logger.debug(f"Set required signer: {pay_vkey.hash().to_primitive().hex()}")  # type: ignore

            # --- Build, Sign, Submit ---
            logger.debug("Building and signing transaction...")
            # Cần truyền danh sách khóa ký. Ít nhất là khóa payment.
            # Khóa stake chỉ cần nếu script yêu cầu hoặc UTXO input từ ví có stake part.
            signing_keys_list: List[SigningKey | ExtendedSigningKey] = [
                self.signing_key
            ]
            if self.stake_signing_key:
                # Kiểm tra xem input từ ví có cần khóa stake không (thường là cần nếu ví có stake part)
                # Hoặc nếu script yêu cầu (script always_true hiện tại thì không)
                signing_keys_list.append(self.stake_signing_key)

            # Build và ký giao dịch, tiền thừa trả về ví miner
            signed_tx = await asyncio.to_thread(
                builder.build_and_sign,
                signing_keys=signing_keys_list,
                change_address=self.miner_wallet_address,
            )
            # signed_tx = builder.build_and_sign(...) # Nếu build_and_sign là sync

            logger.info(
                f"Submitting self-update transaction (Tx Fee: {signed_tx.transaction_body.fee})..."
            )
            # Submit giao dịch - dùng to_thread nếu context.submit_tx là sync
            tx_id: TransactionId = await asyncio.to_thread(self.context.submit_tx, signed_tx.to_cbor())  # type: ignore
            # tx_id: TransactionId = self.context.submit_tx(signed_tx.to_cbor()) # Nếu submit_tx là sync
            tx_id_str = str(tx_id)
            logger.info(
                f"Miner {self.miner_uid_hex}: Self-update submitted successfully! TxID: {tx_id_str}"
            )
            # Cập nhật cache UTXO sau khi gửi thành công để tránh dùng lại UTXO cũ
            self.last_known_utxo = None
            return tx_id_str

        except Exception as e:
            logger.exception(
                f"Miner {self.miner_uid_hex}: Failed to commit self-update: {e}"
            )
            # Có thể log thêm thông tin builder để debug nếu cần
            # logger.error(f"Transaction builder state: Inputs={getattr(builder,'inputs',[])}, Outputs={getattr(builder,'outputs',[])}")
            return None

    async def run(self, validator_api_url: str, check_interval_seconds: int = 60):
        """
        Vòng lặp chính của Miner Agent: Fetch kết quả -> Tìm UTXO -> Tính Datum -> Commit.
        """
        logger.info(f"MinerAgent for {self.miner_uid_hex} starting run loop...")
        while True:
            try:
                # Xác định chu kỳ cần kiểm tra (là chu kỳ tiếp theo sau chu kỳ đã xử lý)
                target_cycle = self.last_processed_cycle + 1
                logger.info(
                    f"Checking for consensus results of cycle {target_cycle}..."
                )

                # 1. Fetch kết quả đồng thuận từ Validator API
                consensus_result = await self.fetch_consensus_result(
                    target_cycle, validator_api_url
                )

                if consensus_result:
                    logger.info(
                        f"Found results for cycle {target_cycle}. Preparing state update."
                    )

                    # 2. Tìm UTXO Datum cũ trên blockchain
                    # Nên tìm lại mỗi lần để đảm bảo lấy đúng UTXO mới nhất
                    old_utxo = await self.find_own_utxo()
                    if not old_utxo:
                        logger.error(
                            f"Cannot proceed with update for cycle {target_cycle}: Own UTXO not found on chain. Will retry."
                        )
                        # Chờ và thử lại ở lần sau
                        await asyncio.sleep(check_interval_seconds)
                        continue
                    if not old_utxo.output.datum:
                        logger.error(
                            f"Cannot proceed with update for cycle {target_cycle}: Found UTXO {old_utxo.input} but it has no inline datum. Will retry."
                        )
                        await asyncio.sleep(check_interval_seconds)
                        continue

                    # Decode datum cũ
                    try:
                        old_datum = MinerDatum.from_cbor(old_utxo.output.datum.cbor)  # type: ignore
                    except Exception as dec_err:
                        logger.error(
                            f"Failed to decode current MinerDatum for UTxO {old_utxo.input}: {dec_err}. Will retry."
                        )
                        await asyncio.sleep(check_interval_seconds)
                        continue

                    # 3. Tính toán Datum mới
                    new_datum = self.calculate_new_datum(
                        old_datum, consensus_result, target_cycle  # type: ignore
                    )

                    if new_datum:
                        # 4. Gửi giao dịch Commit Self-Update
                        tx_id = await self.commit_self_update(old_utxo, new_datum)
                        if tx_id:
                            logger.info(
                                f"Successfully processed and committed update for cycle {target_cycle}. TxID: {tx_id}"
                            )
                            # Cập nhật chu kỳ đã xử lý thành công
                            self.last_processed_cycle = target_cycle
                            # Chờ một chút trước khi kiểm tra chu kỳ tiếp theo
                            # Có thể chờ ít hơn check_interval_seconds để phản ứng nhanh hơn
                            await asyncio.sleep(15)
                        else:
                            logger.error(
                                f"Commit transaction failed for cycle {target_cycle}. Will retry finding UTXO and committing in the next iteration."
                            )
                            # Không tăng last_processed_cycle để thử lại commit cho chu kỳ này
                    else:
                        logger.error(
                            f"Failed to calculate new datum for cycle {target_cycle}. Skipping commit for this cycle."
                        )
                        # Cân nhắc: Có nên tăng last_processed_cycle để bỏ qua chu kỳ lỗi này không?
                        # Tạm thời không tăng để đảm bảo không bỏ lỡ cập nhật.
                        # Nếu lỗi tính toán xảy ra liên tục, cần phải điều tra.

                else:
                    # Chưa có kết quả cho chu kỳ target_cycle
                    logger.info(f"No results found for cycle {target_cycle} yet.")

            except Exception as loop_err:
                # Bắt lỗi không mong muốn trong vòng lặp
                logger.exception(f"Unhandled error in MinerAgent run loop: {loop_err}")
                # Nên có một khoảng chờ dài hơn ở đây để tránh lặp lỗi quá nhanh
                await asyncio.sleep(max(60, check_interval_seconds))

            # Chờ trước khi kiểm tra lại ở vòng lặp tiếp theo
            logger.debug(f"Waiting {check_interval_seconds}s before next check...")
            await asyncio.sleep(check_interval_seconds)

    async def close(self):
        """Đóng các tài nguyên (ví dụ: http client) khi agent dừng."""
        if self.http_client:
            try:
                await self.http_client.aclose()
                logger.info(f"MinerAgent for {self.miner_uid_hex} closed HTTP client.")
            except Exception as e:
                logger.error(
                    f"Error closing HTTP client for MinerAgent {self.miner_uid_hex}: {e}"
                )
