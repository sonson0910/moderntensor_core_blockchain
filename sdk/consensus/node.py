# sdk/consensus/node.py
# ... (Các import giữ nguyên) ...
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
    from sdk.config.settings import settings
except ImportError:
    raise ImportError("CRITICAL: Failed to import settings for ValidatorNode")

# --- Import các module khác ---
# ... (Giữ nguyên các import khác: formulas, metagraph, network, core) ...
from sdk.formulas import * # Import tất cả cho tiện (hoặc import cụ thể)
try:
    from sdk.metagraph import metagraph_data, update_metagraph
    from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum
    # from sdk.metagraph.hash import hash_data, decode_history_from_hash
    def hash_data(data): return f"hashed_{str(data)[:10]}" # Mock hash
    async def decode_history_from_hash(hash_str): await asyncio.sleep(0); return [] # Mock decode
except ImportError:
    logging.warning("sdk.metagraph components not found. Using placeholders.")
    class MinerDatum: pass; 
    class ValidatorDatum: pass; 
    class metagraph_data: pass; 
    class update_metagraph: pass
    def hash_data(data): return f"hashed_{str(data)[:10]}"
    async def decode_history_from_hash(hash_str): await asyncio.sleep(0); return []

try:
    from sdk.network.server import TaskModel, ResultModel
except ImportError:
    logging.warning("sdk.network.server components not found. Using placeholders.")
    class TaskModel: 
        def __init__(self, **kwargs): pass
    class ResultModel: 
        def __init__(self, **kwargs): pass

from sdk.core.datatypes import (
    MinerInfo, ValidatorInfo, TaskAssignment, MinerResult, ValidatorScore
)
try:
    from sdk.network.app.api.v1.endpoints.consensus import ScoreSubmissionPayload
except ImportError:
     logging.warning("Could not import ScoreSubmissionPayload.")
     class ScoreSubmissionPayload: pass

logger = logging.getLogger(__name__)

# --- Xóa định nghĩa Constants ở đây ---
# METAGRAPH_UPDATE_INTERVAL_MINUTES = 60 # Đã chuyển sang settings
# ... xóa các dòng tương tự ...

class ValidatorNode:
    """
    Đại diện cho một node Validator tham gia vào mạng lưới đồng thuận.
    """
    def __init__(self, validator_info: ValidatorInfo, cardano_context: Any, signing_key: Any):
        """
        Khởi tạo Node Validator.
        """
        self.info = validator_info
        self.context = cardano_context
        self.signing_key = signing_key
        self.settings = settings # Sử dụng instance settings đã import
        self.miners_info: Dict[str, MinerInfo] = {}
        self.validators_info: Dict[str, ValidatorInfo] = {}
        self.current_cycle: int = 0
        self.tasks_sent: Dict[str, TaskAssignment] = {}
        self.results_received: Dict[str, List[MinerResult]] = {}
        self.validator_scores: Dict[str, List[ValidatorScore]] = {}
        self.received_validator_scores: Dict[int, Dict[str, Dict[str, ValidatorScore]]] = defaultdict(lambda: defaultdict(dict))
        self.received_scores_lock = asyncio.Lock()
        self.previous_cycle_results: Dict[str, Any] = {"final_miner_scores": {}, "calculated_validator_states": {}}

        # Sử dụng timeout từ settings
        self.http_client = httpx.AsyncClient(
            timeout=self.settings.CONSENSUS_NETWORK_TIMEOUT_SECONDS, # <<<--- Sử dụng settings
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )

        if not self.info.uid:
             raise ValueError("ValidatorInfo must have a valid UID.")
        logger.info(f"Initialized ValidatorNode {self.info.uid} using centralized settings.")

    # --- Tương tác Metagraph ---
    async def load_metagraph_data(self):
        """Tải dữ liệu miners và validators từ Metagraph (async)."""
        logger.info(f"[V:{self.info.uid}] Loading Metagraph data for cycle {self.current_cycle}...")
        start_time = time.time()
        try:
            network = self.settings.CARDANO_NETWORK
            logger.debug(f"Using Cardano network: {network}")

            miner_datums_task = metagraph_data.get_all_miner_data(self.context)
            validator_datums_task = metagraph_data.get_all_validator_data(self.context)
            all_miner_datums, all_validator_datums = await asyncio.gather(
                miner_datums_task, validator_datums_task, return_exceptions=True
            )

            if isinstance(all_miner_datums, Exception): logger.error(f"Failed to fetch miner data: {all_miner_datums}"); all_miner_datums = []
            if isinstance(all_validator_datums, Exception): logger.error(f"Failed to fetch validator data: {all_validator_datums}"); all_validator_datums = []

            logger.info(f"Raw data fetched: {len(all_miner_datums)} miners, {len(all_validator_datums)} validators.")

            temp_miners_info = {}
            datum_divisor = self.settings.METAGRAPH_DATUM_INT_DIVISOR # <<<--- Sử dụng settings
            max_history_len = self.settings.CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN # <<<--- Sử dụng settings

            for datum in all_miner_datums:
                try:
                    uid = getattr(datum, 'uid', None)
                    if not uid: continue
                    # perf_history_hash = getattr(datum, 'performance_history_hash', None)
                    # perf_history = await decode_history_from_hash(perf_history_hash) if perf_history_hash else []
                    perf_history = []
                    temp_miners_info[uid] = MinerInfo(
                        uid=uid,
                        address=getattr(datum, 'address', f'addr_{uid}'),
                        api_endpoint=getattr(datum, 'api_endpoint', None),
                        trust_score=max(0.0, min(1.0, getattr(datum, 'scaled_trust_score', 0) / datum_divisor)), # Sử dụng divisor
                        weight=max(0.0, getattr(datum, 'scaled_weight', 0) / datum_divisor), # Giả sử tên trường là scaled_weight
                        stake=max(0.0, getattr(datum, 'stake', 0)),
                        last_selected_time=max(-1, getattr(datum, 'last_selected_cycle', -1)), # Giả sử tên trường
                        performance_history=perf_history[-max_history_len:] # Sử dụng max_len
                    )
                except Exception as e: logger.warning(f"Failed to parse MinerDatum for UID {getattr(datum, 'uid', 'N/A')}: {e}")

            temp_validators_info = {}
            for datum in all_validator_datums:
                 try:
                    uid = getattr(datum, 'uid', None)
                    if not uid: continue
                    temp_validators_info[uid] = ValidatorInfo(
                        uid=uid,
                        address=getattr(datum, 'address', f'addr_{uid}'),
                        api_endpoint=getattr(datum, 'api_endpoint', None),
                        trust_score=max(0.0, min(1.0, getattr(datum, 'scaled_trust_score', 0) / datum_divisor)), # Sử dụng divisor
                        weight=max(0.0, getattr(datum, 'scaled_weight', 0) / datum_divisor), # Giả sử tên trường
                        stake=max(0.0, getattr(datum, 'stake', 0)),
                    )
                 except Exception as e: logger.warning(f"Failed to parse ValidatorDatum for UID {getattr(datum, 'uid', 'N/A')}: {e}")

            self.miners_info = temp_miners_info
            self.validators_info = temp_validators_info

            if self.info.uid in self.validators_info:
                 loaded_info = self.validators_info[self.info.uid]
                 # ... (cập nhật self.info như trước) ...
                 self.info.address = loaded_info.address
                 self.info.api_endpoint = loaded_info.api_endpoint
                 self.info.trust_score = loaded_info.trust_score
                 self.info.weight = loaded_info.weight
                 self.info.stake = loaded_info.stake
                 logger.info(f"Self validator info ({self.info.uid}) updated from metagraph.")
            elif self.info.uid:
                 self.validators_info[self.info.uid] = self.info
                 logger.warning(f"Self validator ({self.info.uid}) not found in metagraph, added locally.")
            else: logger.error("Current validator info UID is invalid after loading metagraph.")

            load_duration = time.time() - start_time
            logger.info(f"Processed info for {len(self.miners_info)} miners and {len(self.validators_info)} validators in {load_duration:.2f}s.")

        except Exception as e:
            logger.exception(f"Critical error during metagraph data loading: {e}. Cannot proceed this cycle.")
            raise RuntimeError(f"Failed to load metagraph data: {e}") from e


    # ... (Các phương thức select_miners, send/receive, score, P2P giữ nguyên logic,
    #      nhưng đảm bảo truy cập tham số qua self.settings nếu cần, ví dụ:) ...

    def _has_sufficient_scores(self, task_id: str, miner_uid: str, total_active_validators: int) -> bool:
        # ... (logic đếm như cũ) ...
        min_validators = self.settings.CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS # <<<--- Sử dụng settings
        required_count = max(min_validators, int(total_active_validators * 0.6))
        # ...
        return received_count >= required_count

    async def verify_and_penalize_validators(self):
        # ... (logic như cũ, đảm bảo dùng self.settings cho các tham số) ...
        tolerance = self.settings.CONSENSUS_DATUM_COMPARISON_TOLERANCE
        # ...
        slash_amount = calculate_slash_amount(
            validator_info.stake, fraud_severity, self.settings.CONSENSUS_PARAM_MAX_SLASH_RATE
        )
        # ...
        new_trust_score = validator_info.trust_score * (1 - self.settings.CONSENSUS_PARAM_PENALTY_ETA)
        # ...

    def run_consensus_and_penalties(self) -> Tuple[Dict[str, float], Dict[str, Any]]:
        # ... (logic như cũ, đảm bảo dùng self.settings cho các tham số) ...
        new_e_validator = calculate_validator_performance(
            # ...,
            theta1=self.settings.CONSENSUS_PARAM_THETA1,
            theta2=self.settings.CONSENSUS_PARAM_THETA2,
            theta3=self.settings.CONSENSUS_PARAM_THETA3,
            penalty_threshold_dev=self.settings.CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV,
            penalty_k_penalty=self.settings.CONSENSUS_PARAM_PENALTY_K_PENALTY,
            penalty_p_penalty=self.settings.CONSENSUS_PARAM_PENALTY_P_PENALTY
        )
        # ...
        new_val_trust_score = update_trust_score(
             # ...,
             delta_trust=self.settings.CONSENSUS_PARAM_DELTA_TRUST,
             alpha_base=self.settings.CONSENSUS_PARAM_ALPHA_BASE,
             k_alpha=self.settings.CONSENSUS_PARAM_K_ALPHA,
             update_sigmoid_L=self.settings.CONSENSUS_PARAM_UPDATE_SIG_L,
             update_sigmoid_k=self.settings.CONSENSUS_PARAM_UPDATE_SIG_K,
             update_sigmoid_x0=self.settings.CONSENSUS_PARAM_UPDATE_SIG_X0
        )
        # ...
        return final_miner_scores, calculated_validator_states

    def update_miner_state(self, final_scores: Dict[str, float]) -> Dict[str, MinerDatum]:
        # ... (logic như cũ, đảm bảo dùng self.settings cho các tham số) ...
        datum_divisor = self.settings.METAGRAPH_DATUM_INT_DIVISOR
        max_history_len = self.settings.CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN
        # ... (tính toán new_trust_score, new_weight, incentive dùng self.settings.CONSENSUS_PARAM_...) ...
        # Tạo MinerDatum mới...
        # new_datum = MinerDatum(
        #     ...,
        #     scaled_trust_score=int(new_trust_score * datum_divisor),
        #     scaled_weight=int(new_weight * datum_divisor),
        #     performance_history_hash=hash_data(miner_info.performance_history[-max_history_len:]), # Hash phần giới hạn
        #     ...
        # )
        return miner_updates # Dict[str, MinerDatum]

    def prepare_validator_updates(self, calculated_states: Dict[str, Any]) -> Dict[str, ValidatorDatum]:
        # ... (logic như cũ, đảm bảo dùng self.settings nếu cần) ...
        datum_divisor = self.settings.METAGRAPH_DATUM_INT_DIVISOR
        # Tạo ValidatorDatum mới...
        # new_datum = ValidatorDatum(..., scaled_trust_score=int(state.get("trust", 0) * datum_divisor), ...)
        return validator_updates # Dict[str, ValidatorDatum]

    async def commit_updates_to_blockchain(self, miner_updates: Dict[str, MinerDatum], validator_updates: Dict[str, ValidatorDatum]):
        # ... (logic như cũ, cần triển khai thực tế) ...
        pass

    async def run_cycle(self):
        """Thực hiện một chu kỳ đồng thuận hoàn chỉnh (async)."""
        logger.info(f"\n--- Starting Cycle {self.current_cycle} for Validator {self.info.uid} ---")
        cycle_start_time = time.time()
        # Lấy các khoảng thời gian từ settings
        interval_seconds = self.settings.CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
        send_offset_seconds = self.settings.CONSENSUS_SEND_SCORE_OFFSET_MINUTES * 60
        consensus_offset_seconds = self.settings.CONSENSUS_CONSENSUS_TIMEOUT_OFFSET_MINUTES * 60
        commit_offset_seconds = self.settings.CONSENSUS_COMMIT_OFFSET_SECONDS

        # ... (logic tính toán thời điểm như cũ) ...
        metagraph_update_time = cycle_start_time + interval_seconds
        send_score_time = metagraph_update_time - send_offset_seconds
        consensus_timeout_time = metagraph_update_time - consensus_offset_seconds
        commit_time = metagraph_update_time - commit_offset_seconds

        # ... (logic chính của run_cycle như trước, gọi các hàm đã cập nhật) ...
        try:
            await self.verify_and_penalize_validators()
            await self.load_metagraph_data()
            selected_miners = await self.select_miners()
            await self.send_task_and_track(selected_miners)
            receive_timeout = self.settings.CONSENSUS_NETWORK_TIMEOUT_SECONDS * 3 # Ví dụ
            await self.receive_results(timeout=receive_timeout)
            self.score_miner_results()
            # ... (logic chờ, gửi điểm, chờ đồng thuận) ...
            wait_before_send = send_score_time - time.time()
            if wait_before_send > 0: await asyncio.sleep(wait_before_send)
            await self.broadcast_scores()
            wait_for_scores_timeout = consensus_timeout_time - time.time()
            consensus_possible = False
            if wait_for_scores_timeout > 0: consensus_possible = await self.wait_for_consensus_scores(wait_for_scores_timeout)
            else: logger.warning("Not enough time left for consensus.")
            # ... (logic chạy đồng thuận, chuẩn bị update) ...
            final_miner_scores, calculated_validator_states = self.run_consensus_and_penalties()
            self.previous_cycle_results["calculated_validator_states"] = calculated_validator_states
            self.previous_cycle_results["final_miner_scores"] = final_miner_scores
            miner_updates = self.update_miner_state(final_miner_scores)
            validator_updates = self.prepare_validator_updates(calculated_validator_states)
            # ... (logic chờ commit) ...
            wait_before_commit = commit_time - time.time()
            if wait_before_commit > 0: await asyncio.sleep(wait_before_commit)
            else: logger.warning("Commit time passed!")
            # ... (commit) ...
            await self.commit_updates_to_blockchain(miner_updates, validator_updates)

        except Exception as e: logger.exception(f"Error during cycle {self.current_cycle}: {e}")
        finally:
            # ... (logic kết thúc chu kỳ, dọn dẹp như cũ) ...
            cycle_end_time = time.time()
            logger.info(f"--- Cycle {self.current_cycle} Finished (Duration: {cycle_end_time - cycle_start_time:.1f}s) ---")
            self.current_cycle += 1
            cleanup_cycle = self.current_cycle - 3
            async with self.received_scores_lock:
                 if cleanup_cycle in self.received_validator_scores: del self.received_validator_scores[cleanup_cycle]; logger.info(f"Cleaned up scores for cycle {cleanup_cycle}")


# --- Hàm chạy chính (Ví dụ Async) ---
async def main_validator_loop():
    logger.info("Starting validator node loop...")
    if not settings: logger.error("Settings not loaded. Exiting."); return

    # --- Load thông tin validator từ settings ---
    validator_uid = settings.VALIDATOR_UID
    validator_address = settings.VALIDATOR_ADDRESS
    api_endpoint = settings.VALIDATOR_API_ENDPOINT
    if not validator_uid or not validator_address or not api_endpoint:
        logger.error("Validator UID, Address, or API Endpoint not configured. Exiting.")
        return

    if not ValidatorInfo or not ValidatorNode: logger.error("Node classes not available. Exiting."); return

    # TODO: Load signing key thực tế từ file/env được bảo vệ
    signing_key = None # Placeholder - Cần khóa ký thực tế

    my_validator_info = ValidatorInfo(uid=validator_uid, address=validator_address, api_endpoint=api_endpoint)
    # cardano_ctx = await cardano_service.get_context_async(settings) # Cần context thực tế

    # Tạo node validator (truyền signing_key)
    validator_node = ValidatorNode(my_validator_info, cardano_context=None, signing_key=signing_key)

    # --- Inject instance vào dependency của FastAPI ---
    try:
        from sdk.network.app.dependencies import set_validator_node_instance
        set_validator_node_instance(validator_node)
        logger.info("Validator node instance injected into API dependency.")
    except Exception as e: logger.error(f"Could not inject validator node into API dependency: {e}")

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
    except asyncio.CancelledError: logger.info("Main node loop cancelled.")
    except Exception as e: logger.exception(f"Exception in main node loop: {e}")
    finally:
        await validator_node.http_client.aclose()
        logger.info("Main node loop finished.")

if __name__ == "__main__":
    try:
        if settings: asyncio.run(main_validator_loop())
        else: print("Could not load settings. Aborting.")
    except KeyboardInterrupt: print("\nInterrupted by user.")

