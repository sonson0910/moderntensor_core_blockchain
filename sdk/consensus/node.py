# sdk/consensus/node.py
"""
Định nghĩa lớp ValidatorNode chứa logic chính điều phối chu trình đồng thuận.
Sử dụng asyncio cho các tác vụ mạng và chờ đợi.
Sử dụng đối tượng settings tập trung từ sdk.config.settings.
*** Đây là khung sườn chi tiết, cần hoàn thiện logic cụ thể ***
"""
import os
import random
import time
import json
import math
import asyncio
import httpx
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict, OrderedDict
import logging

# --- Import Settings ---
from sdk.config.settings import settings

# --- Import các module khác trong SDK ---
# Formulas
from sdk.formulas import *  # Import tất cả hoặc import cụ thể

# Metagraph & Blockchain Interaction
from sdk.core.datatypes import CycleConsensusResults, MinerConsensusResult
from sdk.metagraph.metagraph_data import get_all_miner_data, get_all_validator_data
from sdk.metagraph import metagraph_data, update_metagraph
from sdk.metagraph.metagraph_datum import (
    MinerDatum,
    ValidatorDatum,
    STATUS_ACTIVE,
    STATUS_JAILED,
    STATUS_INACTIVE,
)
from sdk.smartcontract.validator import read_validator
from sdk.metagraph.hash.hash_datum import hash_data  # Import hàm hash thật sự
from sdk.keymanager.decryption_utils import decode_hotkey_skey


# from sdk.metagraph.hash import hash_data, decode_history_from_hash # Cần hàm hash/decode
async def decode_history_from_hash(hash_str):
    await asyncio.sleep(0)
    return []  # Mock decode


# Network Models (for task/result data structure)
from sdk.network.server import TaskModel, ResultModel

# Core Datatypes
from sdk.core.datatypes import (
    MinerInfo,
    ValidatorInfo,
    TaskAssignment,
    MinerResult,
    ValidatorScore,
)
from sdk.service.context import get_chain_context

# Pydantic model for API communication
# from sdk.network.app.api.v1.endpoints.consensus import ScoreSubmissionPayload
# PyCardano types
from pycardano import (
    Network,
    Address,
    ScriptHash,
    BlockFrostChainContext,
    PaymentSigningKey,
    StakeSigningKey,
    TransactionId,
    UTxO,
    ExtendedSigningKey,
)

# --- Import các hàm logic đã tách ra ---
from .selection import select_miners_logic
from .scoring import score_results_logic
from .p2p import broadcast_scores_logic
from .state import (
    run_consensus_logic,
    verify_and_penalize_logic,
    prepare_miner_updates_logic,
    prepare_validator_updates_logic,
    commit_updates_logic,
)

# --- Logging ---
logger = logging.getLogger(__name__)


class ValidatorNode:
    """
    Lớp điều phối chính cho Validator Node.
    Quản lý trạng thái và gọi các hàm logic từ các module con.
    """

    def __init__(
        self,
        validator_info: ValidatorInfo,
        cardano_context: BlockFrostChainContext,
        signing_key: ExtendedSigningKey,
        stake_signing_key: Optional[ExtendedSigningKey] = None,
        state_file="validator_state.json",
    ):
        """
        Khởi tạo Node Validator.

        Args:
            validator_info: Thông tin của validator này (UID, Address, API Endpoint).
            cardano_context: Context để tương tác Cardano (BlockFrostChainContext).
            signing_key: Khóa ký thanh toán (PaymentSigningKey) của validator.
            stake_signing_key: Khóa ký stake (StakeSigningKey) nếu có.
        """
        if not validator_info or not validator_info.uid:
            raise ValueError("Valid ValidatorInfo with a UID must be provided.")
        if not cardano_context:
            raise ValueError(
                "Cardano context (e.g., BlockFrostChainContext) must be provided."
            )
        if not signing_key:
            raise ValueError("PaymentSigningKey must be provided.")

        self.info = validator_info
        self.context = cardano_context
        self.signing_key = signing_key
        self.stake_signing_key = stake_signing_key
        self.settings = settings  # Sử dụng instance settings đã import
        self.state_file = state_file  # Lưu đường dẫn file
        self.current_cycle: int = self._load_last_cycle()
        self.miners_selected_for_cycle: Set[str] = set()

        self.network = Network.TESTNET

        # State variables
        self.miners_info: Dict[str, MinerInfo] = {}
        self.validators_info: Dict[str, ValidatorInfo] = {}
        self.current_utxo_map: Dict[str, UTxO] = {}  # Map: uid_hex -> UTxO object
        self.tasks_sent: Dict[str, TaskAssignment] = {}
        self.cycle_scores: Dict[str, List[ValidatorScore]] = defaultdict(
            list
        )  # Điểm tích lũy của cả chu kỳ
        self.miner_is_busy: Set[str] = set()  # UID hex của miner đang bận
        self.results_buffer: Dict[str, MinerResult] = {}  # {task_id: MinerResult}
        self.results_buffer_lock = asyncio.Lock()
        self.validator_scores: Dict[str, List[ValidatorScore]] = {}  # Điểm do mình chấm
        self.consensus_results_cache: OrderedDict[int, CycleConsensusResults] = (
            OrderedDict()
        )
        self.consensus_results_cache_lock = asyncio.Lock()
        self.max_cache_cycles = 3  # Có thể cấu hình qua settings

        # P2P score sharing state
        self.received_validator_scores: Dict[
            int, Dict[str, Dict[str, ValidatorScore]]
        ] = defaultdict(lambda: defaultdict(dict))
        self.received_scores_lock = asyncio.Lock()

        # State for cross-cycle verification
        self.previous_cycle_results: Dict[str, Any] = {
            "final_miner_scores": {},
            "calculated_validator_states": {},
        }

        # HTTP client for P2P communication
        timeout = getattr(
            self.settings, "HTTP_TIMEOUT_SECONDS", 30.0
        )  # Lấy từ settings hoặc mặc định
        self.http_client = httpx.AsyncClient(timeout=timeout)

        # Load script details once
        try:
            validator_details = read_validator()
            if (
                not validator_details
                or "script_hash" not in validator_details
                or "script_bytes" not in validator_details
            ):
                raise ValueError(
                    "Failed to load valid script details (hash or bytes missing)."
                )
            self.script_hash: ScriptHash = validator_details["script_hash"]
            self.script_bytes = validator_details["script_bytes"]
        except Exception as e:
            logger.exception(
                "Failed to read validator script details during node initialization."
            )
            raise ValueError(
                f"Could not initialize node due to script loading error: {e}"
            ) from e

        logger.info(f"Initialized ValidatorNode {self.info.uid} with Mini-Batch Logic.")
        logger.info(
            f"Initialized ValidatorNode {self.info.uid} using centralized settings."
        )
        logger.info(f"Contract Script Hash: {self.script_hash}")
        logger.info(f"Cardano Network: {self.settings.CARDANO_NETWORK}")

    def _load_last_cycle(self) -> int:
        """Tải chu kỳ cuối cùng từ file trạng thái."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state_data = json.load(f)
                    last_cycle = state_data.get("last_completed_cycle", -1)
                    logger.info(
                        f"Loaded last completed cycle {last_cycle} from {self.state_file}"
                    )
                    # Chu kỳ hiện tại sẽ là chu kỳ tiếp theo
                    return last_cycle + 1
            else:
                logger.warning(
                    f"State file {self.state_file} not found. Starting from cycle 0."
                )
                return 0
        except Exception as e:
            logger.error(
                f"Error loading state file {self.state_file}: {e}. Starting from cycle 0."
            )
            return 0

    def _save_current_cycle(self):
        """Lưu chu kỳ *vừa hoàn thành* vào file trạng thái."""
        # Chu kỳ vừa hoàn thành là self.current_cycle - 1 (sau khi run_cycle tăng lên)
        cycle_to_save = self.current_cycle - 1
        if cycle_to_save < 0:
            return  # Chưa hoàn thành chu kỳ nào

        state_data = {"last_completed_cycle": cycle_to_save}
        try:
            with open(self.state_file, "w") as f:
                json.dump(state_data, f)
            logger.debug(
                f"Saved last completed cycle {cycle_to_save} to {self.state_file}"
            )
        except Exception as e:
            logger.error(f"Error saving state file {self.state_file}: {e}")

    # --- Thêm phương thức mới để lấy kết quả từ cache ---
    async def get_consensus_results_for_cycle(
        self, cycle_num: int
    ) -> Optional[CycleConsensusResults]:
        """Lấy kết quả đồng thuận đã lưu cho một chu kỳ cụ thể."""
        async with self.consensus_results_cache_lock:
            return self.consensus_results_cache.get(cycle_num)

    # --- Thêm phương thức mới để công bố/lưu kết quả ---
    async def _publish_consensus_results(
        self,
        cycle: int,
        final_miner_scores: Dict[str, float],
        calculated_rewards: Dict[str, float],
    ):
        """
        (Placeholder) Lưu kết quả đồng thuận vào cache để API có thể truy cập.
        Trong tương lai có thể mở rộng để ký, đưa lên IPFS, hoặc commit hash on-chain.
        """
        logger.info(
            f"[V:{self.info.uid}] Caching consensus results for cycle {cycle}..."
        )
        results_for_miners: Dict[str, MinerConsensusResult] = {}

        # Lấy tất cả miner IDs từ final_scores hoặc calculated_rewards
        all_miner_ids = set(final_miner_scores.keys()) | set(calculated_rewards.keys())

        for miner_uid_hex in all_miner_ids:
            p_adj = final_miner_scores.get(
                miner_uid_hex, 0.0
            )  # Mặc định 0 nếu không có điểm
            incentive = calculated_rewards.get(
                miner_uid_hex, 0.0
            )  # Mặc định 0 nếu không có thưởng

            # Tạo đối tượng kết quả cho miner này
            # Note: hiện tại chưa tính sẵn trust_score mới cho miner ở đây
            # vì việc đó miner sẽ tự làm khi cập nhật.
            miner_result = MinerConsensusResult(
                miner_uid=miner_uid_hex, p_adj=p_adj, calculated_incentive=incentive
            )
            results_for_miners[miner_uid_hex] = miner_result

        # Tạo đối tượng kết quả cho cả chu kỳ
        cycle_results = CycleConsensusResults(
            cycle=cycle,
            results=results_for_miners,
            publisher_uid=(
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            ),  # Đã bỏ comment và thêm uid
            # signature=... # Thêm chữ ký sau
        )

        # Lưu vào cache (dùng OrderedDict để giới hạn kích thước)
        async with self.consensus_results_cache_lock:
            self.consensus_results_cache[cycle] = cycle_results
            # Giữ cache trong giới hạn kích thước
            while len(self.consensus_results_cache) > self.max_cache_cycles:
                self.consensus_results_cache.popitem(last=False)  # Xóa item cũ nhất

        logger.info(
            f"Consensus results for cycle {cycle} cached ({len(results_for_miners)} miners). Ready for API access."
        )
        # TODO (Future): Implement actual publication (IPFS, On-chain hash, Signed API)

    # --- Tương tác Metagraph ---
    async def load_metagraph_data(self):
        """
        Tải dữ liệu miners và validators từ Metagraph bằng cách gọi các hàm
        trong sdk.metagraph.metagraph_data và cập nhật trạng thái node.
        """
        logger.info(
            f"[V:{self.info.uid}] Loading Metagraph data for cycle {self.current_cycle}..."
        )
        start_time = time.time()
        network = self.network
        datum_divisor = self.settings.METAGRAPH_DATUM_INT_DIVISOR
        max_history_len = self.settings.CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN

        previous_miners_info = self.miners_info.copy()
        previous_validators_info = self.validators_info.copy()

        self.current_utxo_map = {}
        temp_miners_info = {}
        temp_validators_info = {}
        try:
            # Gọi đồng thời để tải dữ liệu
            miner_data_task = get_all_miner_data(
                self.context, self.script_hash, network
            )
            validator_data_task = get_all_validator_data(self.context, self.script_hash, network)  # type: ignore
            # TODO: Thêm task load Subnet/Foundation data nếu cần

            all_miner_dicts, all_validator_dicts = await asyncio.gather(
                miner_data_task, validator_data_task, return_exceptions=True
            )

            # Xử lý lỗi fetch
            if isinstance(all_miner_dicts, Exception):
                logger.error(f"Failed to fetch miner data: {all_miner_dicts}")
                all_miner_dicts = []
            if isinstance(all_validator_dicts, Exception):
                logger.error(f"Failed to fetch validator data: {all_validator_dicts}")
                all_validator_dicts = []

            logger.info(f"Fetched {len(all_miner_dicts)} miner entries and {len(all_validator_dicts)} validator entries.")  # type: ignore

            # --- Chuyển đổi Miner dicts sang MinerInfo ---
            for utxo_object, datum_dict in all_miner_dicts:  # type: ignore
                try:
                    uid_hex = datum_dict.get("uid")
                    if not uid_hex:
                        continue

                    on_chain_history_hash_hex = datum_dict.get(
                        "performance_history_hash"
                    )
                    on_chain_history_hash_bytes = (
                        bytes.fromhex(on_chain_history_hash_hex)
                        if on_chain_history_hash_hex
                        else None
                    )

                    current_local_history = []  # Mặc định là rỗng
                    previous_info = previous_miners_info.get(uid_hex)
                    if previous_info:
                        current_local_history = (
                            previous_info.performance_history
                        )  # Lấy lịch sử cũ từ bộ nhớ

                    verified_history = []  # Lịch sử sẽ được lưu vào MinerInfo mới
                    if on_chain_history_hash_bytes:
                        # Nếu có hash on-chain, thử xác minh lịch sử cục bộ
                        if current_local_history:
                            try:
                                local_history_hash = hash_data(current_local_history)
                                if local_history_hash == on_chain_history_hash_bytes:
                                    verified_history = current_local_history  # Hash khớp, giữ lại lịch sử cục bộ
                                    logger.debug(
                                        f"Miner {uid_hex}: Local history verified against on-chain hash."
                                    )
                                else:
                                    logger.warning(
                                        f"Miner {uid_hex}: Local history hash mismatch! Resetting history. (Local: {local_history_hash.hex()}, OnChain: {on_chain_history_hash_bytes.hex()})"
                                    )
                                    verified_history = []  # Hash không khớp, reset
                            except Exception as hash_err:
                                logger.error(
                                    f"Miner {uid_hex}: Error hashing local history: {hash_err}. Resetting history."
                                )
                                verified_history = []
                        else:
                            # Có hash on-chain nhưng không có lịch sử cục bộ -> không thể xác minh
                            logger.warning(
                                f"Miner {uid_hex}: On-chain history hash found, but no local history available. Resetting history."
                            )
                            verified_history = []
                    else:
                        # Không có hash on-chain (có thể là miner mới)
                        logger.debug(
                            f"Miner {uid_hex}: No on-chain history hash found. Using current local (likely empty)."
                        )
                        verified_history = current_local_history  # Giữ lại lịch sử cục bộ (thường là rỗng)

                    # Đảm bảo giới hạn độ dài
                    verified_history = verified_history[-max_history_len:]

                    wallet_addr_hash_hex = datum_dict.get("wallet_addr_hash")
                    wallet_addr_hash_bytes = (
                        bytes.fromhex(wallet_addr_hash_hex)
                        if wallet_addr_hash_hex
                        else None
                    )

                    temp_miners_info[uid_hex] = MinerInfo(
                        uid=uid_hex,
                        address=datum_dict.get(
                            "address", f"addr_miner_{uid_hex[:8]}..."
                        ),
                        api_endpoint=datum_dict.get("api_endpoint"),
                        trust_score=float(datum_dict.get("trust_score", 0.0)),
                        weight=float(datum_dict.get("weight", 0.0)),
                        stake=float(datum_dict.get("stake", 0)),
                        last_selected_time=int(
                            datum_dict.get("last_selected_time", -1)
                        ),
                        performance_history=verified_history,  # <<< SỬ DỤNG LỊCH SỬ ĐÃ XÁC MINH
                        subnet_uid=int(datum_dict.get("subnet_uid", -1)),
                        status=int(datum_dict.get("status", STATUS_INACTIVE)),
                        registration_slot=int(datum_dict.get("registration_slot", 0)),
                        wallet_addr_hash=wallet_addr_hash_bytes,
                        performance_history_hash=on_chain_history_hash_bytes,  # Lưu lại hash on-chain (bytes)
                    )

                    # --- Lưu UTXO vào map ---
                    self.current_utxo_map[uid_hex] = utxo_object
                except Exception as e:
                    logger.warning(
                        f"Failed to parse Miner data dict for UID {datum_dict.get('uid', 'N/A')}: {e}",
                        exc_info=False,
                    )
                    logger.debug(f"Problematic miner data dict: {datum_dict}")

            # --- Chuyển đổi Validator dicts sang ValidatorInfo ---
            for utxo_object, datum_dict in all_validator_dicts:  # type: ignore
                try:
                    uid_hex = datum_dict.get("uid")
                    if not uid_hex:
                        continue

                    # Lấy hash từ datum (bytes)
                    on_chain_history_hash_hex = datum_dict.get(
                        "performance_history_hash"
                    )
                    on_chain_history_hash_bytes = (
                        bytes.fromhex(on_chain_history_hash_hex)
                        if on_chain_history_hash_hex
                        else None
                    )

                    current_local_history = []
                    previous_info = previous_validators_info.get(uid_hex)
                    if previous_info and hasattr(
                        previous_info, "performance_history"
                    ):  # Kiểm tra có thuộc tính không
                        current_local_history = previous_info.performance_history

                    verified_history = []
                    if on_chain_history_hash_bytes:
                        if current_local_history:
                            try:
                                local_history_hash = hash_data(current_local_history)
                                if local_history_hash == on_chain_history_hash_bytes:
                                    verified_history = current_local_history
                                    logger.debug(
                                        f"Validator {uid_hex}: Local history verified."
                                    )
                                else:
                                    logger.warning(
                                        f"Validator {uid_hex}: History hash mismatch! Resetting."
                                    )
                                    verified_history = []
                            except Exception as hash_err:
                                logger.error(
                                    f"Validator {uid_hex}: Error hashing local history: {hash_err}. Resetting."
                                )
                                verified_history = []
                        else:
                            logger.warning(
                                f"Validator {uid_hex}: On-chain hash found, no local history. Resetting."
                            )
                            verified_history = []
                    else:
                        logger.debug(
                            f"Validator {uid_hex}: No on-chain history hash. Using current local."
                        )
                        verified_history = current_local_history

                    verified_history = verified_history[-max_history_len:]

                    # --- Lấy address bytes từ datum và decode ---
                    # Lấy các hash khác
                    wallet_addr_hash_hex = datum_dict.get("wallet_addr_hash")
                    wallet_addr_hash_bytes = (
                        bytes.fromhex(wallet_addr_hash_hex)
                        if wallet_addr_hash_hex
                        else None
                    )
                    # ------------------------------------------

                    temp_validators_info[uid_hex] = ValidatorInfo(
                        uid=uid_hex,
                        address=datum_dict.get(
                            "address", f"addr_validator_{uid_hex[:8]}..."
                        ),
                        api_endpoint=datum_dict.get("api_endpoint"),
                        trust_score=float(datum_dict.get("trust_score", 0.0)),
                        weight=float(datum_dict.get("weight", 0.0)),
                        stake=float(datum_dict.get("stake", 0)),
                        last_performance=float(datum_dict.get("last_performance", 0.0)),
                        performance_history=verified_history,
                        subnet_uid=int(datum_dict.get("subnet_uid", -1)),
                        status=int(datum_dict.get("status", STATUS_INACTIVE)),
                        registration_slot=int(datum_dict.get("registration_slot", 0)),
                        wallet_addr_hash=wallet_addr_hash_bytes,
                        performance_history_hash=on_chain_history_hash_bytes,  # Lưu lại hash on-chain
                    )
                    logger.debug(
                        f"  Loaded Validator Peer: UID={uid_hex}, Status={datum_dict.get('status', 'N/A')}, Endpoint='{datum_dict.get('api_endpoint', 'N/A')}'"
                    )
                    self.current_utxo_map[uid_hex] = utxo_object
                except Exception as e:
                    logger.warning(
                        f"Failed to parse Validator data dict for UID {datum_dict.get('uid', 'N/A')}: {e}",
                        exc_info=False,
                    )
                    logger.debug(f"Problematic validator data dict: {datum_dict}")

            # --- Cập nhật trạng thái node ---
            self.miners_info = temp_miners_info
            self.validators_info = temp_validators_info

            # Cập nhật thông tin của chính mình
            self_uid_hex = (
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            )
            if self_uid_hex in self.validators_info:
                loaded_info = self.validators_info[self_uid_hex]
                #  self.info.address = loaded_info.address
                self.info.api_endpoint = loaded_info.api_endpoint
                self.info.trust_score = loaded_info.trust_score
                self.info.weight = loaded_info.weight
                self.info.stake = loaded_info.stake
                # Cập nhật thêm các trường khác nếu cần
                logger.info(
                    f"Self validator info ({self_uid_hex}) updated from metagraph."
                )
            elif self.info.uid:
                self.validators_info[self_uid_hex] = self.info
                logger.warning(
                    f"Self validator ({self_uid_hex}) not found in metagraph, added locally. Ensure initial state is correct."
                )
            else:
                logger.error(
                    "Current validator info UID is invalid after loading metagraph."
                )

            # TODO: Load và xử lý dữ liệu Subnet/Foundation nếu cần

            load_duration = time.time() - start_time
            logger.info(
                f"Processed info for {len(self.miners_info)} miners and {len(self.validators_info)} validators in {load_duration:.2f}s."
            )
            logger.info(
                f"UTXO map populated with {len(self.current_utxo_map)} entries."
            )

        except Exception as e:
            logger.exception(
                f"Critical error during metagraph data loading/processing: {e}. Cannot proceed this cycle."
            )
            self.current_utxo_map = {}
            self.miners_info = {}
            self.validators_info = {}
            raise RuntimeError(f"Failed to load and process metagraph data: {e}") from e

    # --- Lựa chọn Miner ---
    def select_miners(self) -> List[MinerInfo]:
        """Chọn miners để giao việc."""
        logger.info(
            f"[V:{self.info.uid}] Selecting miners for cycle {self.current_cycle}..."
        )
        num_to_select = self.settings.CONSENSUS_NUM_MINERS_TO_SELECT
        beta = self.settings.CONSENSUS_PARAM_BETA
        max_time_bonus = self.settings.CONSENSUS_PARAM_MAX_TIME_BONUS
        # Gọi hàm logic từ selection.py
        return select_miners_logic(
            miners_info=self.miners_info,
            current_cycle=self.current_cycle,
            num_to_select=num_to_select,  # Truyền số lượng cần chọn
            beta=beta,  # Truyền hệ số beta
            max_time_bonus=max_time_bonus,  # Truyền giới hạn bonus thời gian
        )

    def _select_available_miners_for_batch(self, num_to_select: int) -> List[MinerInfo]:
        """
        Chọn một lô các miner khả dụng (không bận) và đang hoạt động (active)
        sử dụng logic lựa chọn chính.

        Args:
            num_to_select: Số lượng miner mong muốn cho lô (N).

        Returns:
            Danh sách các đối tượng MinerInfo cho các miner khả dụng được chọn,
            tối đa num_to_select miner. Trả về list rỗng nếu không có miner phù hợp.
        """
        # 1. Lọc các miner đang hoạt động (active)
        active_miners_all = [
            m
            for m in self.miners_info.values()
            if getattr(m, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]
        if not active_miners_all:
            logger.debug("Mini-batch selection: No active miners found.")
            return []

        # 2. Lọc tiếp các miner không bận (uid không có trong self.miner_is_busy)
        available_miners = [
            m for m in active_miners_all if m.uid not in self.miner_is_busy
        ]

        if not available_miners:
            # Không log warning vì đây là trường hợp bình thường khi chờ miner xử lý xong
            logger.debug(
                "Mini-batch selection: No available (not busy) active miners found at the moment."
            )
            return []

        logger.debug(
            f"Mini-batch selection: {len(available_miners)} available miners to choose from."
        )

        # 3. Chuẩn bị đầu vào cho logic lựa chọn chính (cần một dict)
        available_miners_dict = {m.uid: m for m in available_miners}

        # 4. Lấy các tham số lựa chọn từ settings
        beta = self.settings.CONSENSUS_PARAM_BETA
        max_time_bonus = self.settings.CONSENSUS_PARAM_MAX_TIME_BONUS

        # 5. Gọi logic lựa chọn hiện có (select_miners_logic) trên nhóm miner khả dụng
        #    Giới hạn số lượng chọn bằng số lượng thực tế khả dụng
        actual_num_to_select = min(num_to_select, len(available_miners))
        if actual_num_to_select <= 0:
            return []  # Không có ai để chọn

        # Gọi hàm logic từ selection.py
        selected_miners_for_batch = select_miners_logic(
            miners_info=available_miners_dict,
            current_cycle=self.current_cycle,  # Sử dụng cycle hiện tại để tính bonus time
            num_to_select=actual_num_to_select,  # Chọn tối đa N
            beta=beta,
            max_time_bonus=max_time_bonus,
        )

        logger.debug(
            f"Mini-batch selection: Selected {len(selected_miners_for_batch)} miners for this batch: {[m.uid for m in selected_miners_for_batch]}"
        )
        return selected_miners_for_batch

    # --- Giao Task ---
    # --- 1. Đánh dấu _create_task_data ---
    def _create_task_data(self, miner_uid: str) -> Any:
        """
        (Trừu tượng/Cần Override) Tạo dữ liệu task cụ thể cho một miner.

        Lớp Validator kế thừa cho từng Subnet PHẢI override phương thức này
        để định nghĩa nội dung và định dạng task phù hợp với bài toán AI.

        Raises:
            NotImplementedError: Nếu không được override.
        """
        logger.error(
            f"'_create_task_data' must be implemented by the inheriting Validator class for miner {miner_uid}."
        )
        raise NotImplementedError(
            "Subnet Validator must implement task creation logic."
        )

    # --- Phương thức helper mới để gửi task lô ---
    # async def _send_task_batch(
    #     self, miners_to_send: List[MinerInfo], batch_num: int
    # ) -> Dict[str, TaskAssignment]:
    #     """Gửi một lô task đến các miner được chỉ định và trả về dict các task đã gửi thành công."""
    #     tasks_to_send_coroutines = []
    #     tasks_sent_successfully: Dict[str, TaskAssignment] = {}
    #     miners_sent_to = []  # Giữ thứ tự để khớp với results

    #     if not miners_to_send:
    #         return tasks_sent_successfully

    #     logger.info(f"Preparing to send task batch to {len(miners_to_send)} miners...")

    #     for miner_info in miners_to_send:
    #         miner_uid = miner_info.uid
    #         # Đánh dấu bận ngay
    #         self.miner_is_busy.add(miner_uid)

    #         # Tạo task ID duy nhất (thêm timestamp nhỏ hoặc số thứ tự batch nếu cần)
    #         task_id = f"task_{self.current_cycle}_{self.info.uid}_{miner_uid}_b{batch_num}_{random.randint(1000,9999)}"
    #         try:
    #             task_data = self._create_task_data(miner_uid)
    #             if task_data is None:
    #                 raise ValueError("_create_task_data returned None")
    #             task = TaskModel(task_id=task_id, **task_data)
    #         except Exception as e:
    #             logger.exception(f"Failed to create task for miner {miner_uid}: {e}")
    #             self.miner_is_busy.discard(miner_uid)  # Hủy đánh dấu bận
    #             continue  # Bỏ qua miner này

    #         assignment = TaskAssignment(
    #             task_id=task_id,
    #             task_data=task_data,
    #             miner_uid=miner_uid,
    #             validator_uid=self.info.uid,
    #             timestamp_sent=time.time(),
    #             expected_result_format={},  # Cập nhật nếu cần
    #         )
    #         self.tasks_sent[task_id] = assignment  # Thêm vào danh sách chờ tổng
    #         tasks_sent_successfully[task_id] = assignment  # Thêm vào danh sách lô này
    #         miners_sent_to.append(miner_info)  # Lưu lại miner đã gửi

    #         tasks_to_send_coroutines.append(
    #             self._send_task_via_network_async(miner_info.api_endpoint, task)  # type: ignore
    #         )

    #     # Gửi task đi
    #     if tasks_to_send_coroutines:
    #         logger.info(
    #             f"Sending batch of {len(tasks_to_send_coroutines)} tasks concurrently..."
    #         )
    #         results = await asyncio.gather(
    #             *tasks_to_send_coroutines, return_exceptions=True
    #         )

    #         # Xử lý lỗi gửi
    #         success_count = 0
    #         for i, result in enumerate(results):
    #             if i < len(miners_sent_to):
    #                 miner_info_sent = miners_sent_to[i] # Lấy miner theo đúng thứ tự gửi
    #                 # Tìm assignment tương ứng trong lô đã gửi thành công
    #                 assignment_key_to_find = None
    #                 for task_id_key, assign_val in tasks_sent_successfully.items():
    #                     if assign_val.miner_uid == miner_info_sent.uid:
    #                         # Giả định chỉ gửi 1 task/miner/batch, nếu gửi nhiều cần logic phức tạp hơn
    #                         assignment_key_to_find = task_id_key
    #                         break

    #                 if assignment_key_to_find:
    #                     assign = tasks_sent_successfully[assignment_key_to_find]
    #                     if isinstance(result, bool) and result:
    #                         success_count += 1
    #                     else:
    #                         logger.warning(f"Failed send task {assign.task_id} to {assign.miner_uid}: {result}. Marking available.")
    #                         self.miner_is_busy.discard(assign.miner_uid)
    #                         if assign.task_id in self.tasks_sent: del self.tasks_sent[assign.task_id]
    #                         del tasks_sent_successfully[assign.task_id] # Xóa khỏi dict trả về
    #                 else:
    #                     # Lỗi logic: Không tìm thấy assignment cho miner đã gửi?
    #                     logger.error(f"Could not find assignment for miner {miner_info_sent.uid} in successfully sent batch after gather.")

    #             else: logger.error("Result index mismatch during send processing.")
    #     else:
    #         logger.warning("No tasks were actually sent in this batch.")

    #     return tasks_sent_successfully

    async def _send_task_batch(
        self, miners_for_batch: List[MinerInfo], batch_num: int
    ) -> Dict[str, TaskAssignment]:
        """
        Creates and sends tasks to a specific batch of miners asynchronously.
        Marks miners as busy and tracks successfully sent tasks.

        Args:
            miners_for_batch: List of MinerInfo objects selected for this batch.
            batch_num: The sequence number of this mini-batch within the cycle.

        Returns:
            A dictionary {task_id: TaskAssignment} for tasks successfully sent
            in this batch. Returns an empty dict if no tasks could be sent.
        """
        if not miners_for_batch:
            logger.info(f"Batch {batch_num}: No miners provided for task sending.")
            return {}

        logger.info(
            f"Batch {batch_num}: Preparing to send tasks to {len(miners_for_batch)} miners..."
        )

        tasks_to_send_coroutines = []
        # Temporary dict to track assignments only for THIS batch before sending
        batch_assignments: Dict[str, TaskAssignment] = {}
        # Keep track of miner UIDs we actually attempt to send to in this batch
        miners_sent_attempted_uids = []

        for miner_info in miners_for_batch:
            miner_uid = miner_info.uid
            # Basic check (already done in selection, but good for safety)
            if not miner_info.api_endpoint or not miner_info.api_endpoint.startswith(
                ("http://", "https://")
            ):
                logger.warning(
                    f"Batch {batch_num}: Miner {miner_uid} has invalid API endpoint ('{miner_info.api_endpoint}'). Skipping."
                )
                continue

            # Create unique task ID including batch number
            # Ensure validator UID is hex string
            self_uid_hex = (
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            )
            task_id = f"task_{self.current_cycle}_{self_uid_hex}_{miner_uid}_b{batch_num}_{random.randint(1000,9999)}"

            try:
                # Create task data using the overridable method
                task_data = self._create_task_data(miner_uid)
                if task_data is None:  # Ensure task data was created
                    raise ValueError("_create_task_data returned None")
                # Assume TaskModel can take task_id and unpack task_data dict
                task = TaskModel(task_id=task_id, **task_data)
            except NotImplementedError:
                logger.error(
                    f"CRITICAL: _create_task_data not implemented by subclass for miner {miner_uid}! Cannot send task."
                )
                continue  # Skip this miner
            except Exception as e:
                logger.exception(
                    f"Batch {batch_num}: Failed to create task for miner {miner_uid}: {e}"
                )
                continue  # Skip this miner

            # Create TaskAssignment
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner_uid,
                validator_uid=self_uid_hex,  # Use hex UID
                timestamp_sent=time.time(),
                expected_result_format={},  # TODO: Define actual expected format if needed
            )

            # --- State Updates Before Sending ---
            self.miner_is_busy.add(miner_uid)  # Mark as busy immediately
            self.tasks_sent[task_id] = assignment  # Add to overall tracking
            batch_assignments[task_id] = assignment  # Add to this batch's tracking
            miners_sent_attempted_uids.append(
                miner_uid
            )  # Track UID for result processing
            # ------------------------------------

            # Prepare the coroutine for sending
            tasks_to_send_coroutines.append(
                self._send_task_via_network_async(miner_info.api_endpoint, task)
            )
            logger.debug(
                f"Batch {batch_num}: Prepared task {task_id} for miner {miner_uid}."
            )

        # --- Send Tasks Concurrently ---
        if not tasks_to_send_coroutines:
            logger.warning(
                f"Batch {batch_num}: No valid tasks could be prepared for sending."
            )
            return {}  # Return empty dict if nothing was prepared

        logger.info(
            f"Batch {batch_num}: Sending {len(tasks_to_send_coroutines)} tasks concurrently..."
        )
        # Gather results (True for success, False/Exception for failure)
        send_results = await asyncio.gather(
            *tasks_to_send_coroutines, return_exceptions=True
        )

        # --- Process Send Results ---
        successful_sends_in_batch = 0
        failed_assignment_keys_in_batch = []

        # Iterate through results, matching them back to miners sent in this batch
        for i, send_result in enumerate(send_results):
            # Ensure index is valid
            if i >= len(miners_sent_attempted_uids):
                logger.error(
                    f"Batch {batch_num}: Result index {i} mismatch with attempted miners."
                )
                continue

            miner_uid_sent = miners_sent_attempted_uids[i]
            # Find the corresponding task_id in this batch
            task_id_for_miner = None
            for tid, assign in batch_assignments.items():
                if assign.miner_uid == miner_uid_sent:
                    task_id_for_miner = tid
                    break

            if not task_id_for_miner:
                logger.error(
                    f"Batch {batch_num}: Could not find assignment for miner {miner_uid_sent} in this batch's tracking."
                )
                continue

            # Check if sending was successful
            if isinstance(send_result, bool) and send_result:
                successful_sends_in_batch += 1
                logger.debug(
                    f"Batch {batch_num}: Successfully sent task {task_id_for_miner} to miner {miner_uid_sent}."
                )
            else:
                # Sending failed
                logger.warning(
                    f"Batch {batch_num}: Failed sending task {task_id_for_miner} to miner {miner_uid_sent}. Error: {send_result}"
                )
                # --- Revert State Updates for Failed Send ---
                self.miner_is_busy.discard(miner_uid_sent)  # Mark as not busy anymore
                if task_id_for_miner in self.tasks_sent:
                    del self.tasks_sent[
                        task_id_for_miner
                    ]  # Remove from overall tracking
                # Mark for removal from the batch's successful assignments
                failed_assignment_keys_in_batch.append(task_id_for_miner)
                # -------------------------------------------

        # Remove failed assignments from the dictionary to be returned
        for task_id_to_remove in failed_assignment_keys_in_batch:
            if task_id_to_remove in batch_assignments:
                del batch_assignments[task_id_to_remove]

        logger.info(
            f"Batch {batch_num}: Sending attempt finished. Successful sends in this batch: {successful_sends_in_batch}/{len(tasks_to_send_coroutines)}."
        )

        # Return only the assignments for tasks successfully sent in this batch
        return batch_assignments

    # --- Phương thức chấm điểm lô mới ---
    def _score_batch_results(self, tasks_in_batch: Dict[str, TaskAssignment]):
        """
        Chấm điểm các kết quả trong buffer tương ứng với các task trong lô này.
        Gán điểm 0 cho các task không có kết quả trong buffer (timeout).
        Cập nhật self.cycle_scores và giải phóng miner khỏi self.miner_is_busy.
        Xóa task đã xử lý khỏi self.tasks_sent.
        """
        logger.info(
            f"Scoring results for {len(tasks_in_batch)} tasks in the current batch..."
        )
        batch_scores_count = 0
        processed_task_ids = set()

        # Lấy kết quả từ buffer (KHÔNG cần lock nếu đây là hàm đồng bộ duy nhất sửa buffer)
        # Tuy nhiên, để an toàn hơn nếu có thể thay đổi cấu trúc sau này, dùng lock:
        # async with self.results_buffer_lock: # Nếu hàm này là async
        #     results_to_score = self.results_buffer.copy()
        #     self.results_buffer.clear()
        # -> Tạm thời giả định đồng bộ và không cần lock khi đọc/clear
        results_to_score = self.results_buffer.copy()
        self.results_buffer.clear()  # Xóa buffer ngay sau khi copy

        for task_id, assignment in tasks_in_batch.items():
            processed_task_ids.add(task_id)  # Đánh dấu task này thuộc về lô đang xử lý
            miner_uid = assignment.miner_uid
            score = 0.0  # Mặc định là 0

            if task_id in results_to_score:
                result = results_to_score[task_id]
                # Kiểm tra lại miner (dù add_miner_result đã kiểm tra)
                if result.miner_uid == miner_uid:
                    try:
                        # Gọi logic chấm điểm cụ thể (cần override bởi Subnet1Validator)
                        score = self._score_individual_result(
                            assignment.task_data, result.result_data
                        )
                        logger.info(
                            f"  Scored Task {task_id} (Miner {miner_uid}): {score:.4f}"
                        )
                        batch_scores_count += 1
                    except Exception as e:
                        logger.exception(
                            f"Error scoring task {task_id} for miner {miner_uid}: {e}. Assigning score 0."
                        )
                        score = 0.0
                else:
                    # Trường hợp này ít xảy ra nếu add_miner_result kiểm tra đúng
                    logger.error(
                        f"Logic Error: Buffered result for task {task_id} has wrong miner {result.miner_uid} (expected {miner_uid}). Assigning score 0."
                    )
                    score = 0.0
            else:
                # Không nhận được kết quả trong thời gian chờ -> điểm 0
                logger.warning(
                    f"No result received in buffer for task {task_id} (Miner {miner_uid}). Assigning score 0."
                )
                score = 0.0

            # Tạo và lưu ValidatorScore vào cycle_scores
            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=miner_uid,
                validator_uid=self.info.uid,
                score=max(0.0, min(1.0, score)),  # Đảm bảo 0 <= score <= 1
            )
            self.cycle_scores[task_id].append(val_score)

            # Đánh dấu miner là rảnh sau khi đã xử lý task của nó trong lô này
            self.miner_is_busy.discard(miner_uid)
            logger.debug(
                f"Miner {miner_uid} marked available after batch scoring for task {task_id}."
            )

            # Xóa task đã xử lý khỏi tasks_sent
            if task_id in self.tasks_sent:
                del self.tasks_sent[task_id]

        # Xử lý các kết quả còn sót lại trong buffer (không thuộc lô này - đến muộn)
        # (Đã clear buffer ở trên nên không cần bước này nữa)

        logger.info(
            f"Finished scoring batch. Scored {batch_scores_count} received results. Assigned 0 to {len(tasks_in_batch) - batch_scores_count} tasks without results in buffer."
        )

        # --- Thêm phương thức này vào class ValidatorNode ---

    # def _score_individual_result(self, task_data: Any, result_data: Any) -> float:
    #     """
    #     Placeholder cho logic chấm điểm của Subnet cụ thể.
    #     Phương thức này BẮT BUỘC phải được override bởi lớp Validator kế thừa.
    #     """
    #     logger.error(f"CRITICAL: Validator {getattr(self, 'info', {}).get('uid', 'UNKNOWN')} is using the base "
    #                  f"'_score_individual_result'. Subnet scoring logic is missing! Returning score 0.0.")
    #     # Hoặc bạn có thể dùng:
    #     # raise NotImplementedError("Subclasses must implement _score_individual_result")
    #     return 0.0

    #     # --- Add this scoring method specific to mini-batches ---

    async def _score_current_batch(self, batch_assignments: Dict[str, TaskAssignment]):
        """
        Scores results for a completed mini-batch, handling timeouts.
        Appends scores (including 0.0 for timeouts) to self.cycle_scores.
        Releases miners from the busy set and removes tasks from tasks_sent.

        Args:
            batch_assignments: Dict {task_id: TaskAssignment} for the batch just finished.
        """
        batch_num_str = (
            ""  # Try to extract batch number for logging if available in task_id
        )
        if batch_assignments:
            first_task_id = next(iter(batch_assignments.keys()))
            parts = first_task_id.split("_b")
            if len(parts) > 1:
                num_part = parts[-1].split("_")[0]
                if num_part.isdigit():
                    batch_num_str = f" (Batch ~{num_part})"

        logger.info(
            f"Scoring results for {len(batch_assignments)} tasks{batch_num_str}..."
        )
        scores_added_count = 0
        timeouts_count = 0

        # Atomically get and clear the current results buffer
        # NOTE: This assumes add_miner_result uses the same lock. If not, acquire lock here.
        # If add_miner_result is sync and called from API thread, this might be okay without async lock.
        # Let's add the lock for safety assuming potential concurrency.
        # This method itself runs synchronously within the main async run_cycle loop.
        # The lock is needed because add_miner_result (called by API) might run concurrently.
        async with self.results_buffer_lock:  # Use the sync version of the lock
            buffered_results_copy = self.results_buffer.copy()
            self.results_buffer.clear()
            logger.debug(
                f"Copied and cleared results buffer. Size was: {len(buffered_results_copy)}"
            )

        # Get validator UID (should be hex string already)
        self_uid_hex = (
            self.info.uid.hex() if isinstance(self.info.uid, bytes) else self.info.uid
        )

        # Iterate through the tasks EXPECTED in this batch
        for task_id, assignment in batch_assignments.items():
            miner_uid = assignment.miner_uid
            score = 0.0
            result_found = False

            # Check if a result for this task_id arrived in the buffer
            if task_id in buffered_results_copy:
                result = buffered_results_copy[task_id]
                result_found = True

                # Double-check miner UID (should be correct if add_miner_result checked)
                if result.miner_uid == miner_uid:
                    try:
                        # ===>>> CALL THE SUBNET-SPECIFIC SCORING LOGIC HERE <<<===
                        # This method MUST be overridden by the specific Validator subclass
                        # (e.g., Subnet1Validator needs to implement this or ensure its
                        # scoring logic is accessible via this call).
                        score = self._score_individual_result(
                            assignment.task_data, result.result_data
                        )
                        logger.info(
                            f"  Task {task_id}: Raw score calculated = {score:.4f} for Miner {miner_uid}"
                        )

                        # Clamp score
                        score = max(0.0, min(1.0, score))
                        scores_added_count += 1
                        logger.debug(
                            f"  Task {task_id}: Scored result from miner {miner_uid}. Score: {score:.4f}"
                        )

                    except NotImplementedError:
                        logger.error(
                            f"CRITICAL: Scoring logic '_score_individual_result' not implemented in {self.__class__.__name__} for task {task_id}! Assigning score 0."
                        )
                        score = 0.0  # Assign 0 if scoring is not implemented
                    except Exception as e:
                        logger.exception(
                            f"  Task {task_id}: Error scoring result from miner {miner_uid}: {e}. Assigning score 0."
                        )
                        score = 0.0  # Assign 0 on scoring error
                else:
                    # This case indicates a potential logic error in how results are buffered/matched
                    logger.error(
                        f"  Task {task_id}: Result in buffer from unexpected miner {result.miner_uid} (expected {miner_uid}). Assigning score 0."
                    )
                    score = 0.0
            else:
                # Timeout for this batch
                timeouts_count += 1
                score = 0.0  # Assign score 0 for timeout
                logger.warning(
                    f"  Task {task_id}: Timeout - No result received from miner {miner_uid} within batch wait time. Assigning score 0."
                )

            # Create ValidatorScore object
            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=miner_uid,
                validator_uid=self_uid_hex,
                score=score,
                timestamp=time.time(),  # Timestamp of scoring
            )

            # Append score to the main cycle accumulator
            # Use defaultdict initialized in __init__
            self.cycle_scores[task_id].append(val_score)

            # --- Release Miner and Task Tracking ---
            self.miner_is_busy.discard(miner_uid)  # Mark miner as available
            if task_id in self.tasks_sent:
                del self.tasks_sent[task_id]  # Remove from overall pending tasks
            # ---------------------------------------

        logger.info(
            f"Batch scoring complete{batch_num_str}. Scores added: {scores_added_count}. Timeouts (Score 0): {timeouts_count}."
        )

    # --- Add this placeholder scoring method (IMPORTANT) ---
    # This NEEDS to be overridden by Subnet1Validator
    def _score_individual_result(self, task_data: Any, result_data: Any) -> float:
        """
        (Placeholder/Needs Override) Calculates score for a single result.

        *** This method MUST be implemented by the specific Validator subclass ***
        (e.g., Subnet1Validator) to contain the actual scoring logic
        (like calling calculate_clip_score).

        Args:
            task_data: Data originally sent in the task.
            result_data: Data received from the miner.

        Returns:
            Score between 0.0 and 1.0.
        """
        logger.error(
            f"CRITICAL: Validator {getattr(self, 'info', {}).get('uid', 'UNKNOWN')} is using the base "
            f"'_score_individual_result'. Subnet scoring logic is missing! Returning score 0.0."
        )
        # In a real scenario, either raise NotImplementedError or implement base logic
        # raise NotImplementedError("Subclasses must implement _score_individual_result")
        return 0.0

    async def _send_task_via_network_async(
        self, miner_endpoint: str, task: TaskModel
    ) -> bool:
        """
        Gửi task qua mạng đến miner endpoint một cách bất đồng bộ.

        Args:
            miner_endpoint: Địa chỉ API của miner (đã bao gồm http/https).
            task: Đối tượng TaskModel chứa thông tin task.

        Returns:
            True nếu gửi thành công (HTTP status 2xx), False nếu có lỗi.
        """
        if not miner_endpoint or not miner_endpoint.startswith(("http://", "https://")):
            logger.warning(
                f"Invalid or missing API endpoint for miner: {miner_endpoint} in task {getattr(task, 'task_id', 'N/A')}"
            )
            return False

        # TODO: Xác định đường dẫn endpoint chính xác trên miner node để nhận task
        # Endpoint này cần được thống nhất giữa validator và miner.
        target_url = f"{miner_endpoint}/receive-task"  # <<<--- GIẢ ĐỊNH ENDPOINT

        try:
            # Serialize task data thành JSON
            # Sử dụng model_dump nếu TaskModel là Pydantic v2, ngược lại dùng dict()
            task_payload = (
                task.model_dump(mode="json")
                if hasattr(task, "model_dump")
                else task.dict()
            )

            logger.debug(f"Sending task {task.task_id} to {target_url}")
            # --- Gửi request POST bằng httpx ---
            response = await self.http_client.post(target_url, json=task_payload)

            # Kiểm tra HTTP status code
            response.raise_for_status()  # Ném exception nếu là 4xx hoặc 5xx

            try:
                response_data = response.json()
                logger.info(
                    f"Successfully sent task {task.task_id} to {miner_endpoint}. Miner Response: {response_data}"
                )
            except json.JSONDecodeError:
                logger.info(
                    f"Successfully sent task {task.task_id} to {miner_endpoint}. Status: {response.status_code} (Non-JSON response)"
                )

            # TODO: Có thể cần xử lý nội dung response nếu miner trả về thông tin xác nhận
            # Ví dụ: data = response.json()
            return True

        except httpx.RequestError as e:
            # Lỗi kết nối mạng, DNS, timeout,...
            logger.error(
                f"Network error sending task {getattr(task, 'task_id', 'N/A')} to {target_url}: {e}"
            )
            return False
        except httpx.HTTPStatusError as e:
            # Lỗi từ phía server miner (4xx, 5xx)
            logger.error(
                f"HTTP error sending task {getattr(task, 'task_id', 'N/A')} to {target_url}: Status {e.response.status_code} - Response: {e.response.text[:200]}"
            )
            return False
        except Exception as e:
            # Các lỗi khác (ví dụ: serialization,...)
            logger.exception(
                f"Unexpected error sending task {getattr(task, 'task_id', 'N/A')} to {target_url}: {e}"
            )
            return False

    async def send_task_and_track(self, miners: List[MinerInfo]):
        """
        Tạo và gửi task cho các miners đã chọn một cách bất đồng bộ,
        đồng thời lưu lại thông tin các task đã gửi thành công.
        """
        if not miners:
            logger.warning("send_task_and_track called with empty miner list.")
            self.tasks_sent = {}
            return

        logger.info(
            f"[V:{self.info.uid}] Attempting to send tasks to {len(miners)} selected miners..."
        )
        self.tasks_sent = {}  # Xóa danh sách task đã gửi của chu kỳ trước
        tasks_to_send = []
        # Tạm lưu assignment để chỉ thêm vào self.tasks_sent nếu gửi thành công
        task_assignments: Dict[str, TaskAssignment] = {}  # {miner_uid: TaskAssignment}

        for miner in miners:
            # Kiểm tra xem miner có endpoint hợp lệ không
            if not miner.api_endpoint or not miner.api_endpoint.startswith(
                ("http://", "https://")
            ):
                logger.warning(
                    f"Miner {miner.uid} has invalid or missing API endpoint ('{miner.api_endpoint}'). Skipping task assignment."
                )
                continue

            if miner.uid == self.info.uid:
                logger.debug(f"Skipping sending task to self (UID: {miner.uid}).")
                continue

            task_id = f"task_{self.current_cycle}_{self.info.uid}_{miner.uid}_{random.randint(1000,9999)}"
            try:
                task_data = self._create_task_data(miner.uid)
                # Giả sử TaskModel có thể tạo từ dict hoặc có constructor phù hợp
                # Cần đảm bảo TaskModel được import đúng
                task = TaskModel(task_id=task_id, **task_data)
            except Exception as e:
                logger.exception(f"Failed to create task for miner {miner.uid}: {e}")
                continue  # Bỏ qua miner này nếu không tạo được task

            # Tạo đối tượng TaskAssignment trước khi gửi
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner.uid,  # Lưu UID dạng hex string
                validator_uid=self.info.uid,  # Lưu UID dạng hex string
                timestamp_sent=time.time(),
                expected_result_format={"output": "tensor", "loss": "float"},  # Ví dụ
            )
            task_assignments[miner.uid] = assignment  # Lưu tạm
            self.tasks_sent[task_id] = assignment
            logger.debug(
                f"Added task {task_id} to self.tasks_sent for miner {miner.uid}"
            )
            # Tạo coroutine để gửi task và thêm vào danh sách chờ
            tasks_to_send.append(
                self._send_task_via_network_async(miner.api_endpoint, task)
            )

        # --- Phần await asyncio.gather và xử lý results ---
        if not tasks_to_send:
            logger.warning("No valid tasks could be prepared for sending.")
            # Cập nhật lại tasks_sent nếu không có task nào được gửi đi? Có thể không cần.
            return  # Thoát nếu không có task nào để gửi

        logger.info(f"Sending {len(tasks_to_send)} tasks concurrently...")
        # Gửi đồng thời tất cả các task
        results = await asyncio.gather(*tasks_to_send, return_exceptions=True)

        successful_sends = 0
        # Xử lý kết quả gửi task
        # Lấy danh sách miners tương ứng với results (những miner thực sự được gửi task)
        miners_with_tasks = [m for m in miners if m.uid in task_assignments]
        for i, result in enumerate(results):
            # Lấy miner tương ứng với kết quả này
            if i < len(miners_with_tasks):
                miner = miners_with_tasks[i]
                assignment = task_assignments.get(miner.uid)
                assignment_check = self.tasks_sent.get(
                    f"task_{self.current_cycle}_{self.info.uid}_{miner.uid}"
                )  # Tìm lại task_id theo cấu trúc
                # Tìm task_id tương ứng với miner trong lần gửi này
                for tid, assign in self.tasks_sent.items():
                    # Kiểm tra cycle và miner uid để đảm bảo đúng task
                    if (
                        tid.startswith(f"task_{self.current_cycle}_")
                        and assign.miner_uid == miner.uid
                    ):
                        current_task_id = tid
                        break

                if current_task_id and isinstance(result, bool) and result:
                    # Gửi thành công, cập nhật last_selected_time
                    if miner.uid in self.miners_info:
                        self.miners_info[miner.uid].last_selected_time = (
                            self.current_cycle
                        )
                        logger.debug(
                            f"Updated last_selected_time for miner {miner.uid} to cycle {self.current_cycle}"
                        )
                    successful_sends += 1
                elif current_task_id:
                    # Gửi thất bại, xóa task khỏi self.tasks_sent? Hoặc đánh dấu là thất bại?
                    # Tạm thời chỉ log lỗi
                    logger.warning(
                        f"Failed to send task {current_task_id} to Miner {miner.uid}. Error/Result: {result}"
                    )
                    # Cân nhắc xóa khỏi tasks_sent để tránh validator chờ kết quả không bao giờ đến
                    # del self.tasks_sent[current_task_id]
                else:
                    logger.error(
                        f"Could not map result index {i} back to a sent task for miner {miner.uid}"
                    )

            else:
                logger.error(
                    f"Result index {i} out of bounds for miners_with_tasks list during task sending result processing."
                )

        logger.info(
            f"Finished sending tasks attempt. Successful sends: {successful_sends}/{len(tasks_to_send)}. Tasks currently tracked: {len(self.tasks_sent)}"
        )

    # --- Nhận và Chấm điểm Kết quả ---
    # --- 2. Sửa receive_results và bỏ _listen_for_results_async ---
    async def _listen_for_results_async(self, timeout: float):
        # <<<--- Bỏ hoàn toàn logic mock này ---<<<
        # Thay vào đó, hàm receive_results sẽ chỉ đơn giản là chờ một khoảng thời gian
        # trong khi kết quả được thêm vào self.results_received thông qua API endpoint.
        pass

    async def receive_results(self, timeout: Optional[float] = None):
        """
        Chờ kết quả từ miner trong một khoảng thời gian.
        Kết quả thực tế được nhận và thêm vào self.results_received
        thông qua API endpoint '/v1/miner/submit_result'.
        """
        if timeout is None:
            receive_timeout_default = (
                self.settings.CONSENSUS_SEND_SCORE_OFFSET_MINUTES * 60 * 0.5
            )  # Ví dụ
            timeout = receive_timeout_default

        logger.info(
            f"[V:{self.info.uid}] Waiting {timeout:.1f}s for miner results via API endpoint..."
        )

        # Đơn giản là đợi hết timeout. Kết quả sẽ được tích lũy trong self.results_received.
        await asyncio.sleep(timeout)

        # Không cần xóa self.results_received ở đây, vì nó được tích lũy qua API.
        # Có thể xóa ở đầu chu kỳ mới hoặc trước khi bắt đầu chờ.
        # => Nên xóa ở đầu hàm này để chỉ xử lý kết quả của chu kỳ hiện tại
        # Tuy nhiên, nếu API nhận kết quả chậm, có thể kết quả chu kỳ trước bị xử lý ở chu kỳ sau?
        # => Cần cơ chế quản lý kết quả theo chu kỳ trong add_miner_result.

        # Tạm thời: Giả định API đủ nhanh và chỉ xử lý kết quả đã nhận trong khoảng timeout
        async with self.results_buffer_lock:  # Lock khi đọc số lượng
            received_count = sum(
                len(res_list) for res_list in self.results_received.values()
            )
            task_ids_with_results = list(self.results_received.keys())

        logger.info(
            f"Finished waiting period. Total results accumulated: {received_count} for tasks: {task_ids_with_results}"
        )
        # Logic xử lý kết quả sẽ diễn ra ở bước score_miner_results

    # -----------------------------------------------------------

    # --- Cập nhật add_miner_result ---
    async def add_miner_result(self, result: MinerResult):
        """
        (API Call Handler) Nhận kết quả, kiểm tra cơ bản và lưu vào buffer.
        """
        if not result or not result.task_id or not result.miner_uid:
            logger.warning("API: Received invalid miner result (missing fields).")
            return False

        # Kiểm tra task ID có đang được mong đợi không (có trong tasks_sent)
        # Dùng get() để tránh lỗi nếu task_id không có (ví dụ đến quá muộn)
        assignment = self.tasks_sent.get(result.task_id)
        if not assignment:
            logger.warning(
                f"API: Received result for unknown/already processed/timed out task_id: {result.task_id} from miner {result.miner_uid}. Ignoring."
            )
            return False  # Từ chối nếu task ID không hợp lệ hoặc đã xử lý xong/timeout

        # Kiểm tra miner gửi có đúng không
        if assignment.miner_uid != result.miner_uid:
            logger.warning(
                f"API: Received result for task {result.task_id} from wrong miner {result.miner_uid}. Expected {assignment.miner_uid}. Ignoring."
            )
            return False

        # --- Lưu vào buffer ---
        async with self.results_buffer_lock:
            if result.task_id in self.results_buffer:
                logger.warning(
                    f"API: Overwriting previous buffered result for task {result.task_id}."
                )
            self.results_buffer[result.task_id] = result
            logger.info(
                f"API: Received and buffered result for task {result.task_id} from miner {result.miner_uid}."
            )
        # --------------------
        return True  # Báo thành công cho API

    # -----------------------------------------

    def score_miner_results(self):
        """Chấm điểm kết quả nhận được."""
        # --- Xóa điểm cũ trước khi chấm ---
        self.validator_scores = {}
        # ---------------------------------

        # --- Lock khi đọc self.results_received ---
        # Tạo bản copy để tránh giữ lock quá lâu nếu scoring chậm
        results_to_score = {}
        # Dùng asyncio.run_coroutine_threadsafe nếu gọi từ thread khác?
        # Hoặc đảm bảo score_miner_results chạy trong cùng event loop
        # Giả sử chạy trong cùng event loop, chỉ cần lock async
        # async with self.results_received_lock: # Không cần lock nếu chỉ đọc sau khi wait xong
        #     results_to_score = self.results_received.copy()
        # => Không cần lock nếu receive_results đợi xong mới gọi score

        # Lấy bản copy để xử lý
        results_to_score = self.results_received.copy()
        # Reset lại dict nhận kết quả cho chu kỳ sau
        self.results_received = defaultdict(list)

        # Gọi hàm logic từ scoring.py (truyền bản copy)
        self.validator_scores = score_results_logic(
            results_received=results_to_score,  # <<<--- Dùng bản copy
            tasks_sent=self.tasks_sent,
            validator_uid=self.info.uid,
        )
        # Hàm score_results_logic sẽ gọi _calculate_score_from_result (cần override)

    async def add_received_score(
        self, submitter_uid: str, cycle: int, scores: List[ValidatorScore]
    ):
        """Thêm điểm số nhận được từ validator khác vào bộ nhớ (async safe)."""
        # Logic này quản lý state nội bộ nên giữ lại trong Node
        # TODO: Thêm validation cho scores và submitter_uid
        async with self.received_scores_lock:
            if cycle not in self.received_validator_scores:
                # Chỉ lưu điểm cho chu kỳ hiện tại hoặc tương lai gần? Tránh lưu trữ quá nhiều.
                if cycle < self.current_cycle - 1:  # Ví dụ: chỉ giữ lại chu kỳ trước đó
                    logger.warning(
                        f"Received scores for outdated cycle {cycle} from {submitter_uid}. Ignoring."
                    )
                    return
                self.received_validator_scores[cycle] = defaultdict(dict)

            valid_scores_added = 0
            for score in scores:
                if not (
                    isinstance(score, ValidatorScore)
                    and isinstance(score.score, (int, float))
                    and 0.0 <= score.score <= 1.0
                    and isinstance(score.task_id, str)
                    and score.task_id
                    and isinstance(score.miner_uid, str)
                    and score.miner_uid
                    and score.validator_uid == submitter_uid
                ):  # Đảm bảo validator_uid khớp người gửi
                    logger.warning(
                        f"Ignoring invalid score object received from {submitter_uid}: {score}"
                    )
                    continue

                if score.task_id not in self.received_validator_scores[cycle]:
                    self.received_validator_scores[cycle][score.task_id] = {}
                # Ghi đè điểm nếu validator gửi lại?
                self.received_validator_scores[cycle][score.task_id][
                    score.validator_uid
                ] = score
                valid_scores_added += 1
                # else:
                #     logger.debug(f"Ignoring score for irrelevant task {score.task_id} from {submitter_uid}")

            logger.debug(
                f"Added {valid_scores_added} scores from {submitter_uid} for cycle {cycle}"
            )

    async def broadcast_scores(
        self, scores_to_broadcast: Dict[str, List[ValidatorScore]]
    ):
        """Gửi điểm số cục bộ đã tích lũy đến các validators khác."""
        # Kiểm tra trạng thái validator (giữ nguyên)
        if self.info.status != STATUS_ACTIVE:
            logger.info(
                f"[V:{self.info.uid}] Skipping score broadcast (status: {self.info.status})."
            )
            return

        # Tính tổng số điểm sẽ gửi
        total_scores = sum(len(v) for v in scores_to_broadcast.values())
        logger.info(
            f"[V:{self.info.uid}] Broadcasting {total_scores} accumulated local scores for cycle {self.current_cycle}..."
        )

        # --- Chuẩn bị danh sách điểm phẳng để gửi ---
        # Hàm broadcast_scores_logic mong đợi một List[ValidatorScore]
        flat_scores_list: List[ValidatorScore] = []
        for task_scores_list in scores_to_broadcast.values():
            flat_scores_list.extend(task_scores_list)
        # ------------------------------------------

        if not flat_scores_list:
            logger.info("No accumulated local scores to broadcast for this cycle.")
            return

        # Gọi hàm logic P2P với danh sách điểm đã làm phẳng
        try:
            await broadcast_scores_logic(
                validator_node=self,  # Truyền self để lấy config, keys...
                local_scores=flat_scores_list,  # Truyền list điểm
            )
        except Exception as e:
            logger.exception(f"Error during broadcast_scores_logic: {e}")

    async def _get_active_validators(self) -> List[ValidatorInfo]:
        """Lấy danh sách validator đang hoạt động."""
        # TODO: Triển khai logic query metagraph thực tế hoặc dùng cache.
        logger.debug("Getting active validators...")
        # Tạm thời lọc từ danh sách đã load, cần đảm bảo danh sách này được cập nhật thường xuyên
        active_vals = [
            v
            for v in self.validators_info.values()
            if v.api_endpoint and getattr(v, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]
        logger.debug(f"Found {len(active_vals)} active validators with API endpoints.")
        return active_vals

    def _has_sufficient_scores(
        self, task_id: str, total_active_validators: int
    ) -> bool:
        """
        Kiểm tra xem đã nhận đủ điểm cho task cụ thể chưa để bắt đầu đồng thuận.
        """
        # Logic này quản lý state nội bộ nên giữ lại trong Node
        current_cycle_scores = self.received_validator_scores.get(
            self.current_cycle, {}
        )
        task_scores = current_cycle_scores.get(task_id, {})
        received_validators_for_task = set(
            task_scores.keys()
        )  # Dùng set để tránh đếm trùng

        # Đếm cả điểm của chính mình (nếu đã chấm)
        # Kiểm tra xem điểm của chính mình đã có trong validator_scores chưa và validator_uid khớp không
        if task_id in self.validator_scores:
            # Kiểm tra xem có score nào trong list của task_id này là của mình không
            if any(
                s.validator_uid == self.info.uid for s in self.validator_scores[task_id]
            ):
                received_validators_for_task.add(
                    self.info.uid
                )  # Thêm UID của mình vào set

        received_count = len(received_validators_for_task)

        # Tính số lượng cần thiết
        min_validators = self.settings.CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS
        # Lấy tỉ lệ phần trăm yêu cầu từ settings (thêm nếu chưa có)
        # required_percentage = self.settings.get('CONSENSUS_REQUIRED_PERCENTAGE', 0.6) # Ví dụ
        required_percentage = 0.6  # Giả định 60%

        # Yêu cầu số lượng tối thiểu HOẶC phần trăm nhất định
        required_count_by_percentage = math.ceil(
            total_active_validators * required_percentage
        )
        required_count = max(min_validators, required_count_by_percentage)

        # Đảm bảo required_count không lớn hơn tổng số validator hoạt động
        required_count = min(required_count, total_active_validators)

        logger.debug(
            f"Scores check for task {task_id}: Received from {received_count}/{required_count} validators (Total active: {total_active_validators}, Min: {min_validators}, %: {required_percentage*100:.0f})"
        )
        return received_count >= required_count

    async def wait_for_consensus_scores(self, wait_timeout_seconds: float) -> bool:
        """
        Chờ nhận đủ điểm số từ các validator khác trong một khoảng thời gian giới hạn.
        """
        logger.info(
            f"Waiting up to {wait_timeout_seconds:.1f}s for consensus scores for cycle {self.current_cycle}..."
        )
        start_wait = time.time()
        active_validators = await self._get_active_validators()
        total_active = len(active_validators)
        min_consensus_validators = self.settings.CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS

        if total_active == 0:
            logger.warning(
                "No active validators found. Skipping wait for consensus scores."
            )
            return False  # Không thể đồng thuận nếu không có ai hoạt động
        elif total_active < min_consensus_validators:
            logger.warning(
                f"Not enough active validators ({total_active}) for minimum consensus ({min_consensus_validators}). Proceeding with available data, but consensus might be weak."
            )
            # Vẫn trả về True để cho phép tính toán, nhưng log cảnh báo
            return True

        # Chỉ kiểm tra các task mà validator này đã chấm điểm (và có thể đã broadcast)
        tasks_to_check = set(self.validator_scores.keys())
        if not tasks_to_check:
            logger.info(
                "No local scores generated, skipping wait for consensus scores."
            )
            return True  # Không có gì để chờ

        logger.debug(f"Waiting for consensus on tasks: {list(tasks_to_check)}")
        processed_task_ids = set()  # Các task đã đủ điểm

        while time.time() - start_wait < wait_timeout_seconds:
            all_relevant_tasks_sufficient = True  # Kiểm tra cho các task cần check
            tasks_still_needing_check = tasks_to_check - processed_task_ids

            if not tasks_still_needing_check:
                logger.info("Sufficient scores received for all relevant tasks.")
                return True  # Đã đủ hết

            async with self.received_scores_lock:  # Lock khi kiểm tra
                # Tạo copy của set để tránh lỗi thay đổi kích thước khi lặp
                for task_id in list(tasks_still_needing_check):
                    if self._has_sufficient_scores(task_id, total_active):
                        logger.debug(f"Task {task_id} now has sufficient scores.")
                        processed_task_ids.add(task_id)
                    else:
                        # Chỉ cần một task chưa đủ là chưa xong
                        all_relevant_tasks_sufficient = False
                        # Vẫn tiếp tục kiểm tra các task khác trong lần lặp này

            if all_relevant_tasks_sufficient and not (
                tasks_to_check - processed_task_ids
            ):
                # Điều kiện này có thể không bao giờ đạt được nếu all_relevant_tasks_sufficient=False ở trên
                # Đã kiểm tra ở đầu vòng lặp rồi.
                pass

            await asyncio.sleep(2)  # Chờ 2 giây rồi kiểm tra lại

        # Nếu vòng lặp kết thúc do timeout
        remaining_tasks = tasks_to_check - processed_task_ids
        if remaining_tasks:
            logger.warning(
                f"Consensus score waiting timed out ({wait_timeout_seconds:.1f}s). Tasks still missing sufficient scores: {list(remaining_tasks)}"
            )
        else:
            logger.info(
                f"Consensus score waiting finished within timeout ({time.time() - start_wait:.1f}s). All relevant tasks have sufficient scores."
            )

        # Trả về True nếu không còn task nào thiếu điểm, False nếu còn
        return not bool(remaining_tasks)

    # --- Kiểm tra và Phạt Validator (Chu kỳ trước) ---
    async def verify_and_penalize_validators(self) -> None:
        """Kiểm tra ValidatorDatum chu kỳ trước và áp dụng phạt."""
        # Gọi hàm logic từ state.py
        # Hàm này sẽ cập nhật self.validators_info trực tiếp nếu có phạt trust
        penalized_updates = await verify_and_penalize_logic(
            current_cycle=self.current_cycle,
            previous_calculated_states=self.previous_cycle_results.get(
                "calculated_validator_states", {}
            ),
            validators_info=self.validators_info,  # Truyền trạng thái hiện tại
            context=self.context,
            settings=self.settings,
            script_hash=self.script_hash,
            network=self.network,
            # signing_key=self.signing_key # Có thể cần nếu commit phạt ngay
        )
        # TODO: Xử lý penalized_updates nếu cần commit ngay hoặc lưu lại
        if penalized_updates:
            logger.warning(
                f"Validators penalized in verification step: {list(penalized_updates.keys())}"
            )
            # Hiện tại chỉ cập nhật trust trong self.validators_info, chưa commit

        return

    # --- Chạy Đồng thuận và Cập nhật Trạng thái ---
    def run_consensus_and_penalties(
        self, self_validator_uid: str, consensus_possible: bool
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """Chạy đồng thuận, tính toán trạng thái mới."""
        # Gọi hàm logic từ state.py
        return run_consensus_logic(
            current_cycle=self.current_cycle,
            tasks_sent=self.tasks_sent,
            received_scores=self.received_validator_scores.get(self.current_cycle, {}),
            validators_info=self.validators_info,
            settings=self.settings,
            consensus_possible=consensus_possible,
            self_validator_uid=self_validator_uid,
        )

    async def update_miner_state(
        self, final_scores: Dict[str, float]
    ) -> Dict[str, MinerDatum]:
        """Chuẩn bị cập nhật trạng thái miners."""
        # Gọi hàm logic từ state.py
        return await prepare_miner_updates_logic(
            current_cycle=self.current_cycle,
            miners_info=self.miners_info,
            final_scores=final_scores,
            settings=self.settings,
            current_utxo_map=self.current_utxo_map,
        )

    async def prepare_validator_updates(
        self, calculated_states: Dict[str, Any]
    ) -> Dict[str, ValidatorDatum]:
        """Chuẩn bị cập nhật trạng thái validator (chỉ cho chính mình)."""
        # Gọi hàm logic từ state.py
        return await prepare_validator_updates_logic(
            current_cycle=self.current_cycle,
            self_validator_info=self.info,
            calculated_states=calculated_states,
            settings=self.settings,
            context=self.context,
        )

    async def commit_updates_to_blockchain(
        self,
        validator_updates: Dict[str, ValidatorDatum],
    ):
        """Gửi giao dịch cập nhật Datum lên blockchain (async)."""
        # Gọi hàm logic từ state.py
        await commit_updates_logic(
            validator_updates=validator_updates,
            current_utxo_map=self.current_utxo_map,
            script_hash=self.script_hash,
            script_bytes=self.script_bytes,
            network=self.network,
            context=self.context,
            signing_key=self.signing_key,
            stake_signing_key=self.stake_signing_key,
            settings=self.settings,
        )

    async def run_cycle(self):
        """
        Thực hiện một chu kỳ đồng thuận hoàn chỉnh (async) theo logic:
        Miner Tự Cập Nhật + Phạt Ngầm Định Validator + Đồng bộ NTP-based.
        """
        logger.info(
            f"\n--- Starting Cycle {self.current_cycle} (Miner Self-Update + Implicit Penalty + NTP Sync) for Validator {self.info.uid} ---"
        )
        cycle_start_time = time.time()  # Ghi lại thời điểm bắt đầu chính xác

        # === 0. Reset State Chu Kỳ ===
        self.cycle_scores = defaultdict(list)
        self.miner_is_busy = set()
        # Xóa điểm P2P đã nhận cho chu kỳ *sắp tới* nếu có (tránh dùng dữ liệu cũ)
        async with self.received_scores_lock:
            if self.current_cycle in self.received_validator_scores:
                del self.received_validator_scores[self.current_cycle]
            self.received_validator_scores[self.current_cycle] = defaultdict(dict)
        # Xóa buffer kết quả miner
        async with self.results_buffer_lock:
            self.results_buffer.clear()
        self.tasks_sent.clear()
        logger.debug(f"Cycle {self.current_cycle}: State reset complete.")

        # === 1. Tính Toán Thời Gian & Mốc Kết Thúc Mục Tiêu ===
        target_cycle_end_time = 0.0  # Khởi tạo
        try:
            interval_seconds = (
                self.settings.CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
            )
            target_cycle_end_time = (
                cycle_start_time + interval_seconds
            )  # Mốc kết thúc tuyệt đối

            tasking_ratio = self.settings.CONSENSUS_TASKING_PHASE_RATIO
            send_offset_seconds = self.settings.CONSENSUS_SEND_SCORE_OFFSET_MINUTES * 60
            consensus_offset_seconds = (
                self.settings.CONSENSUS_CONSENSUS_TIMEOUT_OFFSET_MINUTES * 60
            )
            commit_offset_seconds = self.settings.CONSENSUS_COMMIT_OFFSET_SECONDS
            mini_batch_wait_seconds = self.settings.CONSENSUS_MINI_BATCH_WAIT_SECONDS
            mini_batch_size = self.settings.CONSENSUS_MINI_BATCH_SIZE
            mini_batch_interval_seconds = (
                self.settings.CONSENSUS_MINI_BATCH_INTERVAL_SECONDS
            )

            end_batching_time = cycle_start_time + (interval_seconds * tasking_ratio)
            send_score_time = target_cycle_end_time - send_offset_seconds
            consensus_timeout_time = target_cycle_end_time - consensus_offset_seconds
            commit_time = target_cycle_end_time - commit_offset_seconds

            if not (
                cycle_start_time
                < end_batching_time
                < send_score_time
                < consensus_timeout_time
                < commit_time
                < target_cycle_end_time
            ):
                logger.error(
                    "Cycle timing configuration is illogical. Check offsets and interval."
                )
                # Có thể dừng hoặc điều chỉnh lại thời gian ở đây
                return  # Dừng chu kỳ nếu thời gian lỗi
            logger.info(
                f"Cycle {self.current_cycle} Target End Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(target_cycle_end_time))}"
            )
            logger.info(
                f" - EndBatching={time.strftime('%T', time.localtime(end_batching_time))}, SendScore={time.strftime('%T', time.localtime(send_score_time))}, ConsensusTimeout={time.strftime('%T', time.localtime(consensus_timeout_time))}, Commit={time.strftime('%T', time.localtime(commit_time))}"
            )

        except AttributeError as e:
            logger.error(f"Missing timing config: {e}")
            return
        except Exception as e:
            logger.exception(f"Timing calculation error: {e}")
            return

        # Khởi tạo biến kết quả
        final_miner_scores: Dict[str, float] = {}
        calculated_validator_states: Dict[str, Any] = {}
        validator_self_update: Dict[str, ValidatorDatum] = {}

        try:
            # === BƯỚC 2: KIỂM TRA & PHẠT VALIDATOR (Cập nhật IN-MEMORY) ===
            logger.info(
                "Step 2: Verifying previous cycle validator updates (In-Memory Penalty)..."
            )
            await self.verify_and_penalize_validators()  # Cập nhật self.validators_info
            logger.info("Step 2: Verification/Penalization check completed.")

            # === BƯỚC 3: TẢI DỮ LIỆU METAGRAPH ===
            logger.info("Step 3: Loading Metagraph data...")
            await self.load_metagraph_data()  # Load lại với state đã có thể bị phạt
            logger.info(
                f"Step 3: Metagraph loaded. Miners: {len(self.miners_info)}, Validators: {len(self.validators_info)}"
            )

            # === BƯỚC 4-7: VÒNG LẶP MINI-BATCH (Giao Task & Chấm Điểm Cục Bộ) ===
            if not self.miners_info:
                logger.warning("Step 4-7: No miners found. Skipping tasking phase.")
            else:
                logger.info("Step 4-7: Entering Mini-Batch Tasking Phase...")
                batch_num = 0
                tasks_sent_this_cycle = 0
                while time.time() < end_batching_time:
                    batch_start_time = time.time()
                    batch_num += 1
                    logger.debug(f"--- Starting Mini-Batch {batch_num} ---")

                    # 4a. Chọn miners
                    selected_miners = self._select_available_miners_for_batch(
                        mini_batch_size
                    )
                    if not selected_miners:
                        logger.debug(
                            f"Batch {batch_num}: No available miners. Waiting..."
                        )
                        await asyncio.sleep(mini_batch_interval_seconds)
                        if time.time() >= end_batching_time:
                            logger.info("Tasking time ended while waiting for miners.")
                            break
                        continue

                    # 4b. Gửi task
                    batch_assignments = await self._send_task_batch(
                        selected_miners, batch_num
                    )
                    tasks_sent_this_cycle += len(batch_assignments)
                    if not batch_assignments:
                        logger.warning(f"Batch {batch_num}: Failed to send any tasks.")
                        # Gỡ busy cho miner nếu send fail toàn bộ
                        for m in selected_miners:
                            self.miner_is_busy.discard(m.uid)

                    # 4c. Chờ kết quả
                    time_now = time.time()
                    wait_duration = min(
                        mini_batch_wait_seconds,
                        max(0, end_batching_time - time_now - 1),
                    )  # Chờ hoặc đến hết giờ tasking - 1s
                    logger.debug(
                        f"Batch {batch_num}: Waiting {wait_duration:.1f}s for results (until ~{time.strftime('%T', time.localtime(time_now + wait_duration))})..."
                    )
                    if wait_duration > 0:
                        await asyncio.sleep(wait_duration)
                    logger.debug(f"Batch {batch_num}: Finished waiting period.")

                    # 4d. Chấm điểm lô
                    await self._score_current_batch(
                        batch_assignments
                    )  # Cập nhật self.cycle_scores

                    # Nghỉ giữa các lô nếu còn thời gian
                    if time.time() < end_batching_time:
                        await asyncio.sleep(mini_batch_interval_seconds)
                    else:
                        logger.info("Tasking phase time ended after scoring batch.")
                        break
                logger.info(
                    f"Step 4-7: Mini-Batch Tasking Phase Finished. Total tasks sent: {tasks_sent_this_cycle}"
                )

            # === BƯỚC 8: BROADCAST ĐIỂM CỤC BỘ ===
            wait_before_broadcast_time = send_score_time - time.time()
            if wait_before_broadcast_time > 0:
                logger.info(
                    f"Step 8: Waiting {wait_before_broadcast_time:.1f}s until P2P score broadcast time ({time.strftime('%T', time.localtime(send_score_time))})..."
                )
                await asyncio.sleep(wait_before_broadcast_time)
            accumulated_scores_count = sum(len(v) for v in self.cycle_scores.values())
            logger.info(
                f"Step 8: Broadcasting {accumulated_scores_count} accumulated local scores..."
            )
            await self.broadcast_scores(
                self.cycle_scores
            )  # Truyền dict điểm đã tích lũy

            # === BƯỚC 9: CHỜ NHẬN ĐIỂM P2P ===
            wait_for_scores_timeout = consensus_timeout_time - time.time()
            consensus_possible = False
            if wait_for_scores_timeout > 0:
                logger.info(
                    f"Step 9: Waiting up to {wait_for_scores_timeout:.1f}s for P2P scores (until {time.strftime('%T', time.localtime(consensus_timeout_time))})..."
                )
                consensus_possible = await self.wait_for_consensus_scores(
                    wait_for_scores_timeout
                )
                logger.info(
                    f"Step 9: Consensus possible based on received P2P scores: {consensus_possible}"
                )
            else:
                logger.warning(
                    f"Step 9: Not enough time left ({wait_for_scores_timeout:.1f}s) to wait for consensus scores."
                )
                # Kiểm tra lần cuối
                async with self.received_scores_lock:
                    active_validators = await self._get_active_validators()
                    total_active = len(active_validators)
                    min_validators_needed = (
                        self.settings.CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS
                    )
                    scores_received_count = 0
                    if self.current_cycle in self.received_validator_scores:
                        unique_senders = set()
                        for task_scores in self.received_validator_scores[
                            self.current_cycle
                        ].values():
                            unique_senders.update(task_scores.keys())
                        if self.cycle_scores:
                            unique_senders.add(self.info.uid)
                        scores_received_count = len(unique_senders)
                    if scores_received_count >= min_validators_needed:
                        consensus_possible = True
                        logger.info(
                            f"Sufficient unique validators ({scores_received_count}) sent scores despite timeout."
                        )
                    else:
                        logger.warning(
                            f"Insufficient unique validators ({scores_received_count} < {min_validators_needed}) after timeout."
                        )

            # === BƯỚC 10: CHẠY ĐỒNG THUẬN & TÍNH TOÁN TRẠNG THÁI ===
            logger.info("Step 10: Running final consensus calculations...")
            final_miner_scores, calculated_validator_states = (
                self.run_consensus_and_penalties(
                    consensus_possible=consensus_possible,
                    self_validator_uid=self.info.uid,
                )
            )
            # Lưu kết quả dự kiến cho chu kỳ sau
            self.previous_cycle_results["calculated_validator_states"] = (
                calculated_validator_states.copy()
            )
            self.previous_cycle_results["final_miner_scores"] = (
                final_miner_scores.copy()
            )
            logger.info(
                f"Step 10: Consensus calculation finished. Final miner scores: {len(final_miner_scores)}, Validator states: {len(calculated_validator_states)}"
            )

            # === BƯỚC 11: CÔNG BỐ KẾT QUẢ ĐỒNG THUẬN CHO MINER ===
            logger.info(
                "Step 11: Calculating Miner incentives and Publishing/Caching consensus results..."
            )

            # 11a. Tính toán phần thưởng (incentive) cho từng miner dựa trên kết quả đồng thuận
            calculated_miner_rewards: Dict[str, float] = {}
            if final_miner_scores:
                total_weighted_perf = sum(
                    getattr(minfo, "weight", 0.0) * final_miner_scores.get(uid, 0.0)
                    for uid, minfo in self.miners_info.items()
                    # Chỉ tính cho miner active tại thời điểm load metagraph đầu chu kỳ
                    if getattr(minfo, "status", STATUS_ACTIVE) == STATUS_ACTIVE
                )
                min_total_value = 1.0
                total_system_value = max(min_total_value, total_weighted_perf)
                logger.debug(
                    f"Calculated total_system_value for miner incentive: {total_system_value:.6f}"
                )

                # Lặp qua các miner có điểm đồng thuận để tính incentive
                for miner_uid_hex, p_adj in final_miner_scores.items():
                    miner_info = self.miners_info.get(miner_uid_hex)
                    # Chỉ tính incentive cho miner đang hoạt động
                    if (
                        miner_info
                        and getattr(miner_info, "status", STATUS_ACTIVE)
                        == STATUS_ACTIVE
                    ):
                        try:
                            # Sử dụng trust score của miner *trước khi* cập nhật ở chu kỳ này
                            # (Thường là trust score đã load từ đầu chu kỳ)
                            trust_for_incentive = getattr(
                                miner_info, "trust_score", 0.0
                            )
                            weight_for_incentive = getattr(miner_info, "weight", 0.0)
                            incentive = calculate_miner_incentive(
                                trust_score=trust_for_incentive,
                                miner_weight=weight_for_incentive,
                                # miner_performance_scores chỉ cần chứa P_adj
                                miner_performance_scores=[p_adj],
                                total_system_value=total_system_value,
                                # Lấy các tham số sigmoid từ settings
                                incentive_sigmoid_L=self.settings.CONSENSUS_PARAM_INCENTIVE_SIG_L,
                                incentive_sigmoid_k=self.settings.CONSENSUS_PARAM_INCENTIVE_SIG_K,
                                incentive_sigmoid_x0=self.settings.CONSENSUS_PARAM_INCENTIVE_SIG_X0,
                            )
                            calculated_miner_rewards[miner_uid_hex] = incentive
                            logger.debug(
                                f"Calculated incentive for Miner {miner_uid_hex}: {incentive:.8f} (Trust={trust_for_incentive:.4f}, Weight={weight_for_incentive:.4f}, P_adj={p_adj:.4f})"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error calculating incentive for Miner {miner_uid_hex}: {e}"
                            )
                            calculated_miner_rewards[miner_uid_hex] = (
                                0.0  # Gán 0 nếu lỗi
                            )
                    else:
                        # Miner không hoạt động hoặc không tìm thấy thông tin
                        if miner_info:
                            logger.debug(
                                f"Miner {miner_uid_hex} is not active (status={getattr(miner_info, 'status', 'N/A')}). Skipping incentive calculation."
                            )
                        else:
                            logger.warning(
                                f"MinerInfo not found for {miner_uid_hex} when calculating incentive. Skipping."
                            )
                        calculated_miner_rewards[miner_uid_hex] = 0.0

            # 11b. Gọi hàm để lưu/công bố kết quả (lưu vào cache cho API)
            await self._publish_consensus_results(
                cycle=self.current_cycle,
                final_miner_scores=final_miner_scores,
                calculated_rewards=calculated_miner_rewards,  # Truyền phần thưởng đã tính
            )
            logger.info("Step 11: Consensus results cached/published.")

            # === BƯỚC 12: CHUẨN BỊ CẬP NHẬT VALIDATOR DATUM (CHO CHÍNH MÌNH) ===
            logger.info("Step 12: Preparing self validator datum update...")
            # prepare_validator_updates đọc trust/status hiện tại từ self.info
            validator_self_update = await self.prepare_validator_updates(
                calculated_validator_states
            )
            logger.info(
                f"Step 12: Prepared {len(validator_self_update)} self validator datums."
            )

            # === BƯỚC 13: CHỜ COMMIT ===
            wait_before_commit = commit_time - time.time()
            if wait_before_commit > 0:
                logger.info(
                    f"Step 13: Waiting {wait_before_commit:.1f}s before committing self-update (target: {time.strftime('%T', time.localtime(commit_time))})..."
                )
                await asyncio.sleep(wait_before_commit)
            else:
                logger.warning(
                    f"Step 13: Commit time already passed by {-wait_before_commit:.1f}s! Committing immediately."
                )

            # === BƯỚC 14: COMMIT LÊN BLOCKCHAIN (Chỉ Validator Self-Update) ===
            logger.info("Step 14: Committing SELF validator update to blockchain...")
            await self.commit_updates_to_blockchain(
                validator_updates=validator_self_update,  # Chỉ có self-update
            )
            logger.info("Step 14: Commit process for self-validator initiated.")

        except Exception as e:
            logger.exception(f"Error during consensus cycle {self.current_cycle}: {e}")

        finally:
            # === DỌN DẸP CUỐI CHU KỲ & ĐỒNG BỘ HÓA ===
            cycle_end_time_actual = time.time()  # Thời điểm thực tế kết thúc xử lý
            cycle_duration_actual = cycle_end_time_actual - cycle_start_time
            logger.info(
                f"Cycle {self.current_cycle} internal processing finished (Duration: {cycle_duration_actual:.1f}s)."
            )

            # --- Tính toán thời gian chờ đến mốc chu kỳ tiếp theo ---
            # Sử dụng target_cycle_end_time đã tính ở đầu hàm
            current_time = time.time()
            wait_time_for_sync = target_cycle_end_time - current_time

            if wait_time_for_sync > 0:
                logger.info(
                    f"Waiting {wait_time_for_sync:.1f}s to synchronize end of cycle {self.current_cycle} at target time {time.strftime('%T', time.localtime(target_cycle_end_time))}..."
                )
                await asyncio.sleep(wait_time_for_sync)
            elif wait_time_for_sync < -5:  # Nếu trễ quá 5 giây
                logger.warning(
                    f"Cycle {self.current_cycle} processing exceeded target end time by {-wait_time_for_sync:.1f}s. Starting next cycle immediately."
                )
            else:  # Trễ ít hoặc vừa đúng giờ
                logger.info(
                    f"Cycle {self.current_cycle} finished near target time. Starting next cycle."
                )

            # --- Cập nhật và Lưu trạng thái ---
            completed_cycle = self.current_cycle  # Lưu lại số chu kỳ vừa hoàn thành
            self._save_current_cycle()  # Lưu chu kỳ đã hoàn thành (completed_cycle)
            self.current_cycle += 1  # Tăng lên cho chu kỳ tiếp theo

            # Dọn dẹp P2P scores cũ
            cleanup_cycle = completed_cycle - 2  # Giữ lại dữ liệu 2 chu kỳ trước
            async with self.received_scores_lock:
                if cleanup_cycle in self.received_validator_scores:
                    try:
                        del self.received_validator_scores[cleanup_cycle]
                        logger.info(
                            f"Cleaned up received P2P scores for cycle {cleanup_cycle}"
                        )
                    except KeyError:
                        pass
            logger.info(f"--- End of Cycle {completed_cycle} ---")
            # --- Kết thúc Finally ---


# --- Hàm chạy chính (Đã cập nhật) ---
async def main_validator_loop():
    logger.info("Starting validator node loop...")
    if not settings:
        logger.error("Settings not loaded. Exiting.")
        return

    # --- Khởi tạo context Cardano ---
    cardano_ctx: Optional[BlockFrostChainContext] = None
    try:
        # Lấy context từ hàm get_chain_context (sử dụng cấu hình trong settings)
        cardano_ctx = get_chain_context(method="blockfrost")
        if not cardano_ctx:
            raise ValueError("Failed to get Cardano chain context.")
        logger.info(
            f"Cardano context initialized successfully for network: {settings.CARDANO_NETWORK}"
        )
    except Exception as e:
        logger.exception(f"Failed to initialize Cardano context: {e}")
        return  # Thoát nếu không có context

    # --- Load thông tin validator từ settings ---
    validator_uid = settings.VALIDATOR_UID
    validator_address = settings.VALIDATOR_ADDRESS
    api_endpoint = settings.VALIDATOR_API_ENDPOINT
    if not validator_uid or not validator_address or not api_endpoint:
        logger.error(
            "Validator UID, Address, or API Endpoint not configured in settings. Exiting."
        )
        return

    if not ValidatorInfo or not ValidatorNode:
        logger.error(
            "Node classes (ValidatorInfo/ValidatorNode) not available. Exiting."
        )
        return

    # --- Load signing key thực tế ---
    signing_key: Optional[ExtendedSigningKey] = None
    stake_signing_key: Optional[ExtendedSigningKey] = None
    try:
        logger.info("Attempting to load signing keys using decode_hotkey_skey...")
        base_dir = settings.HOTKEY_BASE_DIR
        coldkey_name = settings.COLDKEY_NAME
        hotkey_name = settings.HOTKEY_NAME
        password = settings.HOTKEY_PASSWORD  # Lưu ý bảo mật khi lấy password

        # Gọi hàm decode để lấy ExtendedSigningKeys
        payment_esk, stake_esk = decode_hotkey_skey(
            base_dir=base_dir,
            coldkey_name=coldkey_name,
            hotkey_name=hotkey_name,
            password=password,
        )
        signing_key = payment_esk  # type: ignore
        stake_signing_key = stake_esk  # type: ignore

        if not signing_key:
            raise ValueError("Failed to load required payment signing key.")

        logger.info(
            f"Successfully loaded keys for hotkey '{hotkey_name}' under coldkey '{coldkey_name}'."
        )

    except FileNotFoundError as fnf_err:
        logger.exception(
            f"Failed to load signing keys: Hotkey file or directory not found. Details: {fnf_err}"
        )
        logger.error(
            f"Please check settings: HOTKEY_BASE_DIR='{settings.HOTKEY_BASE_DIR}', COLDKEY_NAME='{settings.COLDKEY_NAME}', HOTKEY_NAME='{settings.HOTKEY_NAME}'. Exiting."
        )
        return
    except Exception as key_err:
        logger.exception(f"Failed to load/decode signing keys: {key_err}")
        logger.error(
            f"Could not load/decode keys. Check password or key files. Exiting."
        )
        return
    # ---------------------------------

    # Tạo ValidatorInfo từ settings
    # Đảm bảo các giá trị mặc định hợp lý nếu cần
    my_validator_info = ValidatorInfo(
        uid=validator_uid,
        address=validator_address,
        api_endpoint=api_endpoint,
        # Các trường khác như trust, weight, stake sẽ được cập nhật từ metagraph
    )

    # Tạo node validator với context và khóa thực tế
    try:
        validator_node = ValidatorNode(
            validator_info=my_validator_info,
            cardano_context=cardano_ctx,  # <<< Truyền context thực tế
            signing_key=signing_key,  # <<< Truyền ExtendedSigningKey
            stake_signing_key=stake_signing_key,  # <<< Truyền ExtendedSigningKey (hoặc None)
        )
    except Exception as node_init_err:
        logger.exception(f"Failed to initialize ValidatorNode: {node_init_err}")
        return

    # --- Inject instance vào dependency của FastAPI ---
    # Phần này quan trọng nếu bạn chạy vòng lặp này cùng với FastAPI server
    try:
        # Giả sử hàm này nằm trong module dependencies của app FastAPI
        from sdk.network.app.dependencies import set_validator_node_instance

        set_validator_node_instance(validator_node)
        logger.info("Validator node instance injected into API dependency.")
    except ImportError:
        logger.warning(
            "Could not import set_validator_node_instance. API dependencies might not work."
        )
    except Exception as e:
        logger.error(f"Could not inject validator node into API dependency: {e}")

    # --- Chạy vòng lặp chính ---
    try:
        # Chờ một chút để các dịch vụ khác (như FastAPI) có thể khởi động nếu cần
        await asyncio.sleep(5)
        while True:
            cycle_start_time = time.time()
            await validator_node.run_cycle()
            cycle_duration = time.time() - cycle_start_time
            cycle_interval_seconds = (
                settings.CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
            )
            min_wait = settings.CONSENSUS_CYCLE_MIN_WAIT_SECONDS
            wait_time = max(min_wait, cycle_interval_seconds - cycle_duration)
            logger.info(
                f"Cycle duration: {cycle_duration:.1f}s. Waiting {wait_time:.1f}s for next cycle..."
            )
            await asyncio.sleep(wait_time)
    except asyncio.CancelledError:
        logger.info("Main node loop cancelled.")
    except Exception as e:
        logger.exception(f"Exception in main node loop: {e}")
    finally:
        # Dọn dẹp tài nguyên khi vòng lặp kết thúc (ví dụ: đóng http client)
        if hasattr(validator_node, "http_client") and validator_node.http_client:
            await validator_node.http_client.aclose()
        logger.info("Main node loop finished and resources cleaned up.")


# Phần if __name__ == "__main__": giữ nguyên để có thể chạy file này trực tiếp
if __name__ == "__main__":
    try:
        if settings:
            asyncio.run(main_validator_loop())
        else:
            print("Could not load settings. Aborting.")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
