# sdk/consensus/node.py
"""
Định nghĩa lớp ValidatorNode chứa logic chính điều phối chu trình đồng thuận.
Sử dụng asyncio cho các tác vụ mạng và chờ đợi.
Sử dụng đối tượng settings tập trung từ sdk.config.settings.
*** Đây là khung sườn chi tiết, cần hoàn thiện logic cụ thể ***
"""
import random
import time
import math
import asyncio
import httpx
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict
import logging

# --- Import Settings ---
try:
    # Import instance settings đã được load sẵn
    from sdk.config.settings import settings
except ImportError:
    # Nên có cơ chế xử lý lỗi tốt hơn ở đây
    raise ImportError("CRITICAL: Failed to import settings for ValidatorNode")

# --- Import các module khác trong SDK ---
# Formulas
from sdk.formulas import * # Import tất cả hoặc import cụ thể
# Metagraph & Blockchain Interaction
from sdk.metagraph.metagraph_data import get_all_miner_data, get_all_validator_data
from sdk.metagraph import metagraph_data, update_metagraph
from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum, STATUS_ACTIVE, STATUS_JAILED, STATUS_INACTIVE
from sdk.smartcontract.validator import read_validator
# from sdk.metagraph.hash import hash_data, decode_history_from_hash # Cần hàm hash/decode
def hash_data(data): return f"hashed_{str(data)[:10]}" # Mock hash
async def decode_history_from_hash(hash_str): await asyncio.sleep(0); return [] # Mock decode
# Network Models (for task/result data structure)
try:
    from sdk.network.server import TaskModel, ResultModel
except ImportError:
    logging.warning("sdk.network.server components not found. Using placeholders.")
    class TaskModel:
        def __init__(self, task_id: str, data: Any): self.task_id = task_id; self.data = data
        def dict(self): return {"task_id": self.task_id, "data": self.data}
    class ResultModel: pass
# Core Datatypes
from sdk.core.datatypes import (
    MinerInfo, ValidatorInfo, TaskAssignment, MinerResult, ValidatorScore
)
# Pydantic model for API communication
try:
    from sdk.network.app.api.v1.endpoints.consensus import ScoreSubmissionPayload
except ImportError:
     logging.warning("Could not import ScoreSubmissionPayload.")
     class ScoreSubmissionPayload: pass # Placeholder
# PyCardano types
from pycardano import (Network, Address, ScriptHash, BlockFrostChainContext, PaymentSigningKey, StakeSigningKey, TransactionId)

# --- Import các hàm logic đã tách ra ---
try:
    from .selection import select_miners_logic
    from .scoring import score_results_logic
    from .p2p import broadcast_scores_logic
    from .state import (
        run_consensus_logic,
        verify_and_penalize_logic,
        prepare_miner_updates_logic,
        prepare_validator_updates_logic,
        commit_updates_logic
    )
except ImportError as e:
    logging.exception(f"Failed to import consensus logic components: {e}")
    raise

# --- Logging ---
logger = logging.getLogger(__name__)

class ValidatorNode:
    """
    Lớp điều phối chính cho Validator Node.
    Quản lý trạng thái và gọi các hàm logic từ các module con.
    """
    def __init__(self, validator_info: ValidatorInfo, cardano_context: BlockFrostChainContext, signing_key: PaymentSigningKey, stake_signing_key: Optional[StakeSigningKey] = None):
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
             raise ValueError("Cardano context (e.g., BlockFrostChainContext) must be provided.")
        if not signing_key:
             raise ValueError("PaymentSigningKey must be provided.")

        self.info = validator_info
        self.context = cardano_context
        self.signing_key = signing_key
        self.stake_signing_key = stake_signing_key
        self.settings = settings # Sử dụng instance settings đã import

        # State variables
        self.miners_info: Dict[str, MinerInfo] = {}
        self.validators_info: Dict[str, ValidatorInfo] = {}
        self.current_cycle: int = 0 # TODO: Nên load từ trạng thái cuối cùng on-chain/db
        self.tasks_sent: Dict[str, TaskAssignment] = {}
        self.results_received: Dict[str, List[MinerResult]] = {}
        self.validator_scores: Dict[str, List[ValidatorScore]] = {} # Điểm do mình chấm

        # P2P score sharing state
        self.received_validator_scores: Dict[int, Dict[str, Dict[str, ValidatorScore]]] = defaultdict(lambda: defaultdict(dict))
        self.received_scores_lock = asyncio.Lock()

        # State for cross-cycle verification
        self.previous_cycle_results: Dict[str, Any] = {
            "final_miner_scores": {},
            "calculated_validator_states": {}
        }

        # HTTP client for P2P communication
        self.http_client = httpx.AsyncClient(
            timeout=self.settings.CONSENSUS_NETWORK_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20) # Cấu hình giới hạn
        )

        # Load script details once
        try:
            validator_details = read_validator()
            if not validator_details or "script_hash" not in validator_details or "script_bytes" not in validator_details:
                raise ValueError("Failed to load valid script details (hash or bytes missing).")
            self.script_hash: ScriptHash = validator_details["script_hash"]
            self.script_bytes = validator_details["script_bytes"]
        except Exception as e:
            logger.exception("Failed to read validator script details during node initialization.")
            raise ValueError(f"Could not initialize node due to script loading error: {e}") from e

        logger.info(f"Initialized ValidatorNode {self.info.uid} using centralized settings.")
        logger.info(f"Contract Script Hash: {self.script_hash}")
        logger.info(f"Cardano Network: {self.settings.CARDANO_NETWORK}")

    # --- Tương tác Metagraph ---
    async def load_metagraph_data(self):
        """
        Tải dữ liệu miners và validators từ Metagraph bằng cách gọi các hàm
        trong sdk.metagraph.metagraph_data và cập nhật trạng thái node.
        """
        logger.info(f"[V:{self.info.uid}] Loading Metagraph data for cycle {self.current_cycle}...")
        start_time = time.time()
        network = self.settings.CARDANO_NETWORK
        datum_divisor = self.settings.METAGRAPH_DATUM_INT_DIVISOR
        max_history_len = self.settings.CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN

        try:
            # Gọi đồng thời để tải dữ liệu
            miner_data_task = get_all_miner_data(self.context, self.script_hash, network)
            validator_data_task = get_all_validator_data(self.context, self.script_hash, network)
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

            logger.info(f"Fetched {len(all_miner_dicts)} miner entries and {len(all_validator_dicts)} validator entries.")

            # --- Chuyển đổi Miner dicts sang MinerInfo ---
            temp_miners_info = {}
            for miner_dict in all_miner_dicts:
                try:
                    datum = miner_dict.get("datum", {})
                    uid_hex = datum.get("uid")
                    if not uid_hex: continue

                    # TODO: Triển khai logic load và giải mã performance_history_hash
                    # perf_history_hash_hex = datum.get("performance_history_hash")
                    # perf_history = await decode_history_from_hash(perf_history_hash_hex) if perf_history_hash_hex else []
                    perf_history = [] # Placeholder

                    temp_miners_info[uid_hex] = MinerInfo(
                        uid=uid_hex,
                        address=datum.get("address", f"addr_{uid_hex[:8]}..."),
                        api_endpoint=datum.get("api_endpoint"),
                        trust_score=float(datum.get("trust_score", 0.0)),
                        weight=float(datum.get("weight", 0.0)),
                        stake=int(datum.get("stake", 0)),
                        last_selected_time=int(datum.get("last_selected_cycle", -1)),
                        performance_history=perf_history[-max_history_len:],
                        subnet_uid=int(datum.get("subnet_uid", -1)),
                        version=int(datum.get("version", 0)),
                        status=int(datum.get("status", STATUS_INACTIVE)), # Lấy status
                        registration_slot=int(datum.get("registration_slot", 0)),
                        wallet_addr_hash=datum.get("wallet_addr_hash"),
                        performance_history_hash=datum.get("performance_history_hash"),
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse Miner data dict for UID {datum.get('uid', 'N/A')}: {e}", exc_info=False)
                    logger.debug(f"Problematic miner data dict: {miner_dict}")

            # --- Chuyển đổi Validator dicts sang ValidatorInfo ---
            temp_validators_info = {}
            for val_dict in all_validator_dicts:
                 try:
                    datum = val_dict.get("datum", {})
                    uid_hex = datum.get("uid")
                    if not uid_hex: continue

                    temp_validators_info[uid_hex] = ValidatorInfo(
                        uid=uid_hex,
                        address=datum.get("address", f"addr_{uid_hex[:8]}..."),
                        api_endpoint=datum.get("api_endpoint"),
                        trust_score=float(datum.get("trust_score", 0.0)),
                        weight=float(datum.get("weight", 0.0)),
                        stake=int(datum.get("stake", 0)),
                        subnet_uid=int(datum.get("subnet_uid", -1)),
                        version=int(datum.get("version", 0)),
                        status=int(datum.get("status", STATUS_INACTIVE)),
                        registration_slot=int(datum.get("registration_slot", 0)),
                        wallet_addr_hash=datum.get("wallet_addr_hash"),
                        performance_history_hash=datum.get("performance_history_hash"),
                    )
                 except Exception as e:
                    logger.warning(f"Failed to parse Validator data dict for UID {datum.get('uid', 'N/A')}: {e}", exc_info=False)
                    logger.debug(f"Problematic validator data dict: {val_dict}")

            # --- Cập nhật trạng thái node ---
            self.miners_info = temp_miners_info
            self.validators_info = temp_validators_info

            # Cập nhật thông tin của chính mình
            self_uid_hex = self.info.uid.hex() if isinstance(self.info.uid, bytes) else self.info.uid
            if self_uid_hex in self.validators_info:
                 loaded_info = self.validators_info[self_uid_hex]
                 self.info.address = loaded_info.address
                 self.info.api_endpoint = loaded_info.api_endpoint
                 self.info.trust_score = loaded_info.trust_score
                 self.info.weight = loaded_info.weight
                 self.info.stake = loaded_info.stake
                 # Cập nhật thêm các trường khác nếu cần
                 logger.info(f"Self validator info ({self_uid_hex}) updated from metagraph.")
            elif self.info.uid:
                 self.validators_info[self_uid_hex] = self.info
                 logger.warning(f"Self validator ({self_uid_hex}) not found in metagraph, added locally. Ensure initial state is correct.")
            else:
                 logger.error("Current validator info UID is invalid after loading metagraph.")

            # TODO: Load và xử lý dữ liệu Subnet/Foundation nếu cần

            load_duration = time.time() - start_time
            logger.info(f"Processed info for {len(self.miners_info)} miners and {len(self.validators_info)} validators in {load_duration:.2f}s.")

        except Exception as e:
            logger.exception(f"Critical error during metagraph data loading/processing: {e}. Cannot proceed this cycle.")
            raise RuntimeError(f"Failed to load and process metagraph data: {e}") from e

    # --- Lựa chọn Miner ---
    def select_miners(self) -> List[MinerInfo]:
        """Chọn miners để giao việc."""
        logger.info(f"[V:{self.info.uid}] Selecting miners for cycle {self.current_cycle}...")
        # Gọi hàm logic từ selection.py
        return select_miners_logic(
            miners_info=self.miners_info,
            current_cycle=self.current_cycle,
            # Các tham số khác được lấy từ self.settings bên trong hàm logic
        )

    # --- Giao Task ---
    def _create_task_data(self, miner_uid: str) -> Any:
        """Tạo dữ liệu task cụ thể."""
        # TODO: Triển khai logic tạo task phù hợp với ứng dụng AI của bạn
        logger.debug(f"Creating task data for miner {miner_uid}")
        return {"type": "inference", "input_data": f"data_{random.randint(1,1000)}", "model_id": "model_xyz"}

    async def _send_task_via_network_async(self, miner_endpoint: str, task: TaskModel) -> bool:
        """Gửi task qua mạng đến miner endpoint (async)."""
        # TODO: Hoàn thiện logic gửi request và xử lý response/lỗi
        if not miner_endpoint: logger.warning(f"No endpoint for miner in task {getattr(task, 'task_id', 'N/A')}"); return False
        target_url = f"{miner_endpoint}/execute_task" # Giả định endpoint
        try:
            task_payload = task.dict() if hasattr(task, 'dict') else vars(task)
            logger.debug(f"Sending task {task.task_id} to {target_url}")
            # response = await self.http_client.post(target_url, json=task_payload)
            # response.raise_for_status()
            await asyncio.sleep(random.uniform(0.1, 0.3)) # Mock network delay
            logger.info(f"Successfully sent task {task.task_id} to {miner_endpoint}")
            return True
        except Exception as e: logger.error(f"Error sending task {getattr(task, 'task_id', 'N/A')} to {target_url}: {e}"); return False

    async def send_task_and_track(self, miners: List[MinerInfo]):
        """Tạo và gửi task cho các miners đã chọn (async)."""
        # ... (Giữ nguyên logic đã triển khai ở bước trước) ...
        logger.info(f"[V:{self.info.uid}] Attempting to send tasks to {len(miners)} selected miners...")
        # ... (logic tạo task, assignment, gọi gather) ...
        logger.info(f"Finished sending tasks attempt. Successful sends: {successful_sends}/{len(tasks_to_send)}.")

    # --- Nhận và Chấm điểm Kết quả ---
    async def _listen_for_results_async(self, timeout: float) -> Dict[str, List[MinerResult]]:
        """Lắng nghe kết quả trả về từ miner (async)."""
        # TODO: Triển khai logic lắng nghe thực tế (API endpoint, Queue, Websocket...)
        logger.info(f"  (Mock Async) Listening for results for {timeout} seconds...")
        await asyncio.sleep(timeout * 0.1 + random.uniform(1,5)) # Giả lập thời gian chờ + xử lý
        received = {}
        # Logic mock tạo kết quả giả lập
        for task_id, assignment in self.tasks_sent.items():
            if random.random() > 0.15: # 85% thành công trả lời
                 result_data = {"output": [random.random(), random.random()], "loss": random.uniform(0.01, 0.8)}
                 miner_result = MinerResult(task_id=task_id, miner_uid=assignment.miner_uid, result_data=result_data, timestamp_received=time.time())
                 if task_id not in received: received[task_id] = []
                 received[task_id].append(miner_result)
                 logger.debug(f"  (Mock Async) Received result for task {task_id} from Miner {assignment.miner_uid}")
            else:
                 logger.warning(f"  (Mock Async) Timeout or failure for task {task_id} from Miner {assignment.miner_uid}")
        return received

    async def receive_results(self, timeout: float = 60.0):
        """Chờ và nhận kết quả từ miners (async)."""
        logger.info(f"[V:{self.info.uid}] Waiting for results (timeout: {timeout}s)...")
        self.results_received = await self._listen_for_results_async(timeout)
        logger.info(f"Received results for {len(self.results_received)} tasks.")

    def score_miner_results(self):
        """Chấm điểm kết quả nhận được."""
        # Gọi hàm logic từ scoring.py
        self.validator_scores = score_results_logic(
            results_received=self.results_received,
            tasks_sent=self.tasks_sent,
            validator_uid=self.info.uid # Truyền UID dạng hex string
        )

    # --- Trao đổi điểm và Đồng thuận ---
    async def add_received_score(self, submitter_uid: str, cycle: int, scores: List[ValidatorScore]):
        """Thêm điểm số nhận được từ validator khác vào bộ nhớ (async safe)."""
        # ... (Giữ nguyên logic quản lý state nội bộ) ...
        pass

    async def broadcast_scores(self):
        """Gửi điểm số cục bộ đến các validator khác (async)."""
        # Gọi hàm logic từ p2p.py
        active_validators = await self._get_active_validators()
        await broadcast_scores_logic(
            local_scores=self.validator_scores,
            self_validator_info=self.info,
            active_validators=active_validators,
            current_cycle=self.current_cycle,
            http_client=self.http_client
        )

    async def _get_active_validators(self) -> List[ValidatorInfo]:
        """Lấy danh sách validator đang hoạt động."""
        # TODO: Triển khai logic query metagraph thực tế hoặc dùng cache.
        logger.debug("Getting active validators...")
        active_vals = [v for v in self.validators_info.values() if v.api_endpoint and getattr(v, 'status', STATUS_ACTIVE) == STATUS_ACTIVE]
        logger.debug(f"Found {len(active_vals)} active validators with API endpoints.")
        return active_vals

    def _has_sufficient_scores(self, task_id: str, total_active_validators: int) -> bool:
        """Kiểm tra xem đã nhận đủ điểm cho task cụ thể chưa."""
        # ... (Giữ nguyên logic quản lý state nội bộ) ...
        pass

    async def wait_for_consensus_scores(self, wait_timeout_seconds: float) -> bool:
        """Chờ nhận đủ điểm số từ các validator khác."""
        # ... (Giữ nguyên logic quản lý state nội bộ và timing) ...
        pass

    # --- Kiểm tra và Phạt Validator (Chu kỳ trước) ---
    async def verify_and_penalize_validators(self):
        """Kiểm tra ValidatorDatum chu kỳ trước và áp dụng phạt."""
        # Gọi hàm logic từ state.py
        # Hàm này sẽ cập nhật self.validators_info trực tiếp nếu có phạt trust
        penalized_updates = await verify_and_penalize_logic(
            current_cycle=self.current_cycle,
            previous_calculated_states=self.previous_cycle_results.get("calculated_validator_states", {}),
            validators_info=self.validators_info, # Truyền trạng thái hiện tại
            context=self.context,
            settings=self.settings,
            # signing_key=self.signing_key # Có thể cần nếu commit phạt ngay
        )
        # TODO: Xử lý penalized_updates nếu cần commit ngay hoặc lưu lại
        if penalized_updates:
            logger.warning(f"Validators penalized in verification step: {list(penalized_updates.keys())}")
            # Hiện tại chỉ cập nhật trust trong self.validators_info, chưa commit

    # --- Chạy Đồng thuận và Cập nhật Trạng thái ---
    def run_consensus_and_penalties(self) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """Chạy đồng thuận, tính toán trạng thái mới."""
        # Gọi hàm logic từ state.py
        return run_consensus_logic(
            current_cycle=self.current_cycle,
            tasks_sent=self.tasks_sent,
            received_scores=self.received_validator_scores.get(self.current_cycle, {}),
            validators_info=self.validators_info,
            settings=self.settings
        )

    def update_miner_state(self, final_scores: Dict[str, float]) -> Dict[str, MinerDatum]:
        """Chuẩn bị cập nhật trạng thái miners."""
        # Gọi hàm logic từ state.py
        return prepare_miner_updates_logic(
            current_cycle=self.current_cycle,
            miners_info=self.miners_info,
            final_scores=final_scores,
            settings=self.settings,
            # context=self.context # Truyền context nếu cần lấy datum cũ
        )

    async def prepare_validator_updates(self, calculated_states: Dict[str, Any]) -> Dict[str, ValidatorDatum]:
        """Chuẩn bị cập nhật trạng thái validator (chỉ cho chính mình)."""
        # Gọi hàm logic từ state.py
        return await prepare_validator_updates_logic(
            current_cycle=self.current_cycle,
            self_validator_info=self.info,
            calculated_states=calculated_states,
            settings=self.settings,
            context=self.context
        )

    async def commit_updates_to_blockchain(self, miner_updates: Dict[str, MinerDatum], validator_updates: Dict[str, ValidatorDatum]):
        """Gửi giao dịch cập nhật Datum lên blockchain (async)."""
        # Gọi hàm logic từ state.py
        await commit_updates_logic(
            miner_updates=miner_updates,
            validator_updates=validator_updates,
            context=self.context,
            signing_key=self.signing_key,
            stake_signing_key=self.stake_signing_key,
            settings=self.settings
        )

    async def run_cycle(self):
        """Thực hiện một chu kỳ đồng thuận hoàn chỉnh (async)."""
        logger.info(f"\n--- Starting Cycle {self.current_cycle} for Validator {self.info.uid} ---")
        cycle_start_time = time.time()
        # Lấy các khoảng thời gian từ settings
        interval_seconds = self.settings.CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
        send_offset_seconds = self.settings.CONSENSUS_SEND_SCORE_OFFSET_MINUTES * 60
        consensus_offset_seconds = self.settings.CONSENSUS_CONSENSUS_TIMEOUT_OFFSET_MINUTES * 60
        commit_offset_seconds = self.settings.CONSENSUS_COMMIT_OFFSET_SECONDS

        metagraph_update_time = cycle_start_time + interval_seconds
        send_score_time = metagraph_update_time - send_offset_seconds
        consensus_timeout_time = metagraph_update_time - consensus_offset_seconds
        commit_time = metagraph_update_time - commit_offset_seconds

        miner_updates: Dict[str, MinerDatum] = {}
        validator_updates: Dict[str, ValidatorDatum] = {}

        try:
            # Bước 0: Kiểm tra và phạt Validator từ chu kỳ TRƯỚC
            await self.verify_and_penalize_validators()

            # 1. Tải dữ liệu
            await self.load_metagraph_data()
            if not self.miners_info: raise Exception("No miners found in metagraph")

            # 2. Chọn miners
            selected_miners = self.select_miners() # Sync call
            if not selected_miners: raise Exception("No miners selected for task assignment")

            # 3. Gửi task
            await self.send_task_and_track(selected_miners)

            # 4. Nhận kết quả
            receive_timeout = self.settings.CONSENSUS_NETWORK_TIMEOUT_SECONDS * 3 # Ví dụ
            await self.receive_results(timeout=receive_timeout)

            # 5. Chấm điểm cục bộ
            self.score_miner_results() # Sync call

            # 6. Chờ và gửi điểm
            wait_before_send = send_score_time - time.time()
            if wait_before_send > 0: await asyncio.sleep(wait_before_send)
            await self.broadcast_scores()

            # 7. Chờ nhận điểm
            wait_for_scores_timeout = consensus_timeout_time - time.time()
            consensus_possible = False
            if wait_for_scores_timeout > 0:
                 consensus_possible = await self.wait_for_consensus_scores(wait_for_scores_timeout)
            else: logger.warning("Not enough time left for consensus scores.")

            # 8. Chạy đồng thuận, tính toán trạng thái mới
            final_miner_scores, calculated_validator_states = self.run_consensus_and_penalties() # Sync call
            if not consensus_possible: logger.warning("Consensus calculated with potentially incomplete score set.")

            # Lưu kết quả tính toán cho chu kỳ sau
            self.previous_cycle_results["calculated_validator_states"] = calculated_validator_states
            self.previous_cycle_results["final_miner_scores"] = final_miner_scores

            # 9. Chuẩn bị cập nhật trạng thái miner
            miner_updates = self.update_miner_state(final_miner_scores) # Sync call

            # 10. Chuẩn bị cập nhật trạng thái validator (async)
            validator_updates = await self.prepare_validator_updates(calculated_validator_states) # Async call

            # 11. Chờ commit
            wait_before_commit = commit_time - time.time()
            if wait_before_commit > 0: await asyncio.sleep(wait_before_commit)
            else: logger.warning("Commit time already passed!")

            # 12. Commit lên blockchain
            await self.commit_updates_to_blockchain(miner_updates, validator_updates) # Async call

        except Exception as e:
            logger.exception(f"Error during consensus cycle {self.current_cycle}: {e}")

        finally:
            cycle_end_time = time.time()
            logger.info(f"--- Cycle {self.current_cycle} Finished (Duration: {cycle_end_time - cycle_start_time:.1f}s) ---")
            self.current_cycle += 1
            # Dọn dẹp dữ liệu chu kỳ cũ
            cleanup_cycle = self.current_cycle - 3 # Giữ lại dữ liệu 2 chu kỳ trước
            async with self.received_scores_lock:
                 if cleanup_cycle in self.received_validator_scores:
                      del self.received_validator_scores[cleanup_cycle]
                      logger.info(f"Cleaned up received scores for cycle {cleanup_cycle}")


# --- Hàm chạy chính (Ví dụ Async) ---
async def main_validator_loop():
    logger.info("Starting validator node loop...")
    if not settings: logger.error("Settings not loaded. Exiting."); return

    # --- Khởi tạo context Cardano ---
    # cardano_ctx = await cardano_service.get_context_async(settings)

    # --- Load thông tin validator từ settings ---
    validator_uid = settings.VALIDATOR_UID
    validator_address = settings.VALIDATOR_ADDRESS
    api_endpoint = settings.VALIDATOR_API_ENDPOINT
    if not validator_uid or not validator_address or not api_endpoint:
        logger.error("Validator UID, Address, or API Endpoint not configured. Exiting.")
        return

    if not ValidatorInfo or not ValidatorNode: logger.error("Node classes not available. Exiting."); return

    # TODO: Load signing key thực tế từ file/env được bảo vệ
    signing_key: Optional[PaymentSigningKey] = None
    stake_signing_key: Optional[StakeSigningKey] = None
    # Ví dụ load từ file (cần triển khai hàm load_skey)
    # try:
    #     signing_key = load_skey(settings.PAYMENT_SKEY_PATH)
    #     if settings.STAKE_SKEY_PATH:
    #          stake_signing_key = load_skey(settings.STAKE_SKEY_PATH)
    # except Exception as e:
    #     logger.exception(f"Failed to load signing keys: {e}")
    #     return
    if signing_key is None:
         logger.error("Payment signing key could not be loaded. Exiting.")
         return


    my_validator_info = ValidatorInfo(uid=validator_uid, address=validator_address, api_endpoint=api_endpoint)
    # cardano_ctx = ... # Context thực tế

    # Tạo node validator
    validator_node = ValidatorNode(
        validator_info=my_validator_info,
        cardano_context=None, # cardano_ctx
        signing_key=signing_key,
        stake_signing_key=stake_signing_key
    )

    # --- Inject instance vào dependency của FastAPI ---
    try:
        from sdk.network.app.dependencies import set_validator_node_instance
        set_validator_node_instance(validator_node)
        logger.info("Validator node instance injected into API dependency.")
    except Exception as e:
        logger.error(f"Could not inject validator node into API dependency: {e}")

    # --- Chạy vòng lặp chính ---
    try:
        while True:
            cycle_start_time = time.time()
            await validator_node.run_cycle()
            cycle_duration = time.time() - cycle_start_time
            cycle_interval_seconds = settings.CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
            min_wait = settings.CONSENSUS_CYCLE_MIN_WAIT_SECONDS
            wait_time = max(min_wait, cycle_interval_seconds - cycle_duration)
            logger.info(f"Cycle duration: {cycle_duration:.1f}s. Waiting {wait_time:.1f}s for next cycle...")
            await asyncio.sleep(wait_time)
    except asyncio.CancelledError:
        logger.info("Main node loop cancelled.")
    except Exception as e:
        logger.exception(f"Exception in main node loop: {e}")
    finally:
        await validator_node.http_client.aclose()
        logger.info("Main node loop finished.")

if __name__ == "__main__":
    try:
        if settings: asyncio.run(main_validator_loop())
        else: print("Could not load settings. Aborting.")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

