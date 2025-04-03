# sdk/consensus/node.py
"""
Định nghĩa lớp ValidatorNode chứa logic chính điều phối chu trình đồng thuận.
Sử dụng asyncio cho các tác vụ mạng và chờ đợi.
Bổ sung logic kiểm tra và phạt validator cập nhật sai Datum.
"""
import random
import time
import math
import asyncio
import httpx
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict
import logging # Thêm logging

# --- Import từ các module khác trong SDK ---
from sdk.formulas import (
    calculate_selection_probability,
    calculate_adjusted_miner_performance,
    update_trust_score,
    calculate_miner_incentive,
    calculate_validator_performance, # E_validator
    calculate_fraud_severity_value, # Cần logic cụ thể
    calculate_slash_amount,
    calculate_miner_weight,
)
# Giả định các hàm/lớp này tồn tại và có thể import
try:
    from sdk.metagraph import metagraph_data, update_metagraph
    from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum
except ImportError:
    # ... (Placeholder như cũ) ...
    print("Warning: sdk.metagraph components not found. Using placeholders.")
    # ... (Định nghĩa placeholder classes) ...
    class MinerDatum: pass
    class ValidatorDatum: pass
    class metagraph_data:
        @staticmethod
        async def get_all_miner_data(ctx): await asyncio.sleep(0); return []
        @staticmethod
        async def get_all_validator_data(ctx): await asyncio.sleep(0); return []
        @staticmethod
        async def find_miner_utxo(ctx, uid): await asyncio.sleep(0); return None
        @staticmethod
        async def find_validator_utxo(ctx, uid): await asyncio.sleep(0); return None # Thêm hàm tìm UTXO validator
    class update_metagraph:
        @staticmethod
        async def update_miner_datum(ctx, key, utxo, datum): await asyncio.sleep(0); return True
        @staticmethod
        async def update_validator_datum(ctx, key, utxo, datum): await asyncio.sleep(0); return True

try:
    from sdk.network.server import TaskModel, ResultModel
except ImportError:
    # ... (Placeholder như cũ) ...
    print("Warning: sdk.network.server components not found. Using placeholders.")
    class TaskModel: pass
    class ResultModel: pass

# --- Import từ core datatypes ---
from sdk.core.datatypes import (
    MinerInfo, ValidatorInfo, TaskAssignment, MinerResult, ValidatorScore
)
try:
    from sdk.network.app.api.v1.endpoints.consensus import ScoreSubmissionPayload
except ImportError:
     print("Warning: Could not import ScoreSubmissionPayload.")
     class ScoreSubmissionPayload: pass

# --- Hằng số ví dụ ---
METAGRAPH_UPDATE_INTERVAL_MINUTES = 60
SEND_SCORE_OFFSET_MINUTES = 2
CONSENSUS_TIMEOUT_OFFSET_MINUTES = 1
NETWORK_TIMEOUT_SECONDS = 10
VALIDATOR_STATE_COMPARISON_TOLERANCE = 1e-5 # Ngưỡng sai số cho phép khi so sánh float

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ValidatorNode:
    """
    Đại diện cho một node Validator tham gia vào mạng lưới đồng thuận.
    """
    def __init__(self, validator_info: ValidatorInfo, cardano_context: Any, config: Optional[Dict] = None):
        self.info = validator_info
        self.context = cardano_context
        self.miners_info: Dict[str, MinerInfo] = {}
        self.validators_info: Dict[str, ValidatorInfo] = {}
        self.current_cycle: int = 0
        self.tasks_sent: Dict[str, TaskAssignment] = {}
        self.results_received: Dict[str, List[MinerResult]] = {}
        self.validator_scores: Dict[str, List[ValidatorScore]] = {} # Điểm do mình chấm

        self.received_validator_scores: Dict[int, Dict[str, Dict[str, ValidatorScore]]] = defaultdict(lambda: defaultdict(dict))
        self.received_scores_lock = asyncio.Lock()

        # Lưu trữ kết quả tính toán của chu kỳ trước để kiểm tra gian lận
        self.previous_cycle_results: Dict[str, Any] = {
            "final_miner_scores": {}, # {miner_uid: P_adj}
            "calculated_validator_states": {} # {validator_uid: {"E_v": float, "trust": float, ...}}
        }

        self.http_client = httpx.AsyncClient(timeout=NETWORK_TIMEOUT_SECONDS)

        # --- Tải các tham số hệ thống ---
        cfg = config or {}
        # ... (load các tham số như trước) ...
        self.num_miners_to_select = cfg.get('consensus_num_miners_to_select', 5)
        self.min_validators_for_consensus = cfg.get('consensus_min_validators', 3)
        self.param_beta = cfg.get('consensus_param_beta', 0.2)
        self.param_max_time_bonus = cfg.get('consensus_param_max_time_bonus', 10)
        self.param_delta_trust = cfg.get('consensus_param_delta_trust', 0.1)
        self.param_alpha_base = cfg.get('consensus_param_alpha_base', 0.1)
        self.param_k_alpha = cfg.get('consensus_param_k_alpha', 1.0)
        self.param_update_sig_L = cfg.get('consensus_param_update_sig_L', 1.0)
        self.param_update_sig_k = cfg.get('consensus_param_update_sig_k', 5.0)
        self.param_update_sig_x0 = cfg.get('consensus_param_update_sig_x0', 0.5)
        self.param_incentive_sig_L = cfg.get('consensus_param_incentive_sig_L', 1.0)
        self.param_incentive_sig_k = cfg.get('consensus_param_incentive_sig_k', 10.0)
        self.param_incentive_sig_x0 = cfg.get('consensus_param_incentive_sig_x0', 0.5)
        self.param_fraud_threshold_dev = cfg.get('consensus_param_fraud_threshold_dev', 0.3) # Ngưỡng độ lệch để nghi ngờ
        self.param_fraud_n_cycles = cfg.get('consensus_param_fraud_n_cycles', 3)
        self.param_penalty_eta = cfg.get('consensus_param_penalty_eta', 0.5) # Tăng mức phạt trust
        self.param_max_slash_rate = cfg.get('consensus_param_max_slash_rate', 0.2)
        self.param_delta_W = cfg.get('consensus_param_delta_W', 0.5)
        self.param_theta1 = cfg.get('consensus_param_theta1', 0.3)
        self.param_theta2 = cfg.get('consensus_param_theta2', 0.4)
        self.param_theta3 = cfg.get('consensus_param_theta3', 0.3)
        self.param_penalty_threshold_dev = cfg.get('consensus_param_penalty_threshold_dev', 0.1)
        self.param_penalty_k_penalty = cfg.get('consensus_param_penalty_k', 5.0)
        self.param_penalty_p_penalty = cfg.get('consensus_param_penalty_p', 1.0)
        self.param_datum_comparison_tolerance = cfg.get('consensus_datum_tolerance', 1e-5) # Sai số cho phép khi so sánh datum

    # --- Các phương thức load_metagraph, select_miners, send/receive task, score (như trước) ---
    # ... (Giữ nguyên các phương thức này, đảm bảo chúng là async nếu cần) ...
    async def load_metagraph_data(self):
        # ... (Như trước, load cả api_endpoint) ...
        logger.info(f"[V:{self.info.uid}] Loading Metagraph data for cycle {self.current_cycle}...")
        try:
            all_miner_data: List[MinerDatum] = await metagraph_data.get_all_miner_data(self.context)
            all_validator_data: List[ValidatorDatum] = await metagraph_data.get_all_validator_data(self.context)
            # ... (Logic chuyển đổi sang MinerInfo/ValidatorInfo như trước) ...
            self.miners_info = { datum.uid: MinerInfo(...) for datum in all_miner_data } # Cần điền đủ trường
            self.validators_info = { datum.uid: ValidatorInfo(...) for datum in all_validator_data } # Cần điền đủ trường
            if self.info.uid in self.validators_info: self.info = self.validators_info[self.info.uid]
            elif self.info.uid: self.validators_info[self.info.uid] = self.info
            else: logger.error("Current validator info is invalid.")
            logger.info(f"Loaded info for {len(self.miners_info)} miners and {len(self.validators_info)} validators.")
        except Exception as e:
            logger.exception(f"Error loading metagraph data: {e}. Cannot proceed.")
            raise

    async def select_miners(self) -> List[MinerInfo]:
        # ... (Như trước) ...
        logger.info(f"[V:{self.info.uid}] Selecting miners for cycle {self.current_cycle}...")
        # ... (logic tính xác suất và chọn) ...
        selected_miners = list(selected_miners_dict.values())
        logger.info(f"Selected {len(selected_miners)} miners: {[m.uid for m in selected_miners]}")
        return selected_miners

    def _create_task_data(self, miner_uid: str) -> Any:
        # ... (Như trước) ...
        return {"type": "train_step", "data_batch": f"batch_{random.randint(1,100)}", "model_version": "v1.3"}

    async def _send_task_via_network_async(self, miner_endpoint: str, task: TaskModel) -> bool:
        # ... (Như trước, dùng httpx) ...
        if not miner_endpoint: logger.warning(f"No endpoint for miner in task {task.task_id}"); return False
        target_url = f"{miner_endpoint}/receive-task"
        try:
            # response = await self.http_client.post(target_url, json=task.dict())
            # response.raise_for_status()
            logger.debug(f"  (Mock Async) Sent task {task.task_id} to {target_url}")
            await asyncio.sleep(0.1)
            return True
        except Exception as e: logger.error(f"Error sending task {task.task_id} to {target_url}: {e}"); return False

    async def send_task_and_track(self, miners: List[MinerInfo]):
        # ... (Như trước, dùng asyncio.gather) ...
        logger.info(f"[V:{self.info.uid}] Sending tasks...")
        self.tasks_sent = {}
        tasks_to_send = []; task_assignments = {}
        for miner in miners:
            task_id = f"task_{self.current_cycle}_{self.info.uid}_{miner.uid}_{random.randint(1000,9999)}"
            task_data = self._create_task_data(miner.uid)
            task = TaskModel(task_id=task_id, data=task_data)
            assignment = TaskAssignment(...) # Tạo assignment
            task_assignments[miner.uid] = assignment
            tasks_to_send.append(self._send_task_via_network_async(miner.api_endpoint, task))
        results = await asyncio.gather(*tasks_to_send, return_exceptions=True)
        successful_sends = 0
        for i, result in enumerate(results):
            miner = miners[i]; assignment = task_assignments.get(miner.uid)
            if assignment and isinstance(result, bool) and result:
                self.tasks_sent[assignment.task_id] = assignment
                miner.last_selected_time = self.current_cycle
                successful_sends += 1
            else: logger.warning(f"Failed to send task to Miner {miner.uid}. Error: {result}")
        logger.info(f"Successfully sent tasks to {successful_sends} miners.")

    async def _listen_for_results_async(self, timeout: float) -> Dict[str, List[MinerResult]]:
        # ... (Như trước, logic mock) ...
        logger.info(f"  (Mock Async) Listening for results for {timeout} seconds...")
        # ... (logic mock nhận kết quả) ...
        return received # Dict[str, List[MinerResult]]

    async def receive_results(self, timeout: float = 60.0):
        # ... (Như trước) ...
        logger.info(f"[V:{self.info.uid}] Waiting for results...")
        self.results_received = await self._listen_for_results_async(timeout)

    def _calculate_score_from_result(self, task_data: Any, result_data: Any) -> float:
        # ... (Như trước) ...
        score = 0.0
        try:
            loss = float(result_data.get("loss", 1.0)); score = max(0.0, min(1.0, 1.0 - loss * 1.2))
        except (TypeError, ValueError): score = 0.1
        return score

    def score_miner_results(self):
        # ... (Như trước) ...
        logger.info(f"[V:{self.info.uid}] Scoring results...")
        self.validator_scores = {}
        for task_id, results in self.results_received.items():
            # ... (logic chấm điểm và tạo ValidatorScore) ...
            logger.debug(f"  Scored Miner {result.miner_uid} for task {task_id}: {score:.3f}")


    async def add_received_score(self, submitter_uid: str, cycle: int, scores: List[ValidatorScore]):
        # ... (Như trước) ...
        async with self.received_scores_lock:
            # ... (logic thêm điểm vào self.received_validator_scores) ...
            logger.debug(f"Added {len(scores)} scores from {submitter_uid} for cycle {cycle}")

    async def broadcast_scores(self):
        # ... (Như trước, dùng httpx và ScoreSubmissionPayload) ...
        logger.info(f"[V:{self.info.uid}] Broadcasting local scores for cycle {self.current_cycle}...")
        # ... (logic tạo payload và gửi đi) ...
        logger.info(f"Successfully broadcasted scores to {success_count}/{len(broadcast_tasks)} validators.")

    async def _get_active_validators(self) -> List[ValidatorInfo]:
        # ... (Như trước, logic mock) ...
        logger.debug("  (Mock) Getting active validators...")
        await asyncio.sleep(0.1)
        return list(self.validators_info.values())

    def _has_sufficient_scores(self, task_id: str, miner_uid: str, total_active_validators: int) -> bool:
        # ... (Như trước) ...
        # ... (logic kiểm tra số lượng điểm nhận được) ...
        logger.debug(f"Scores check for task {task_id}: Received from {received_count}/{required_count} validators")
        return received_count >= required_count

    async def wait_for_consensus_scores(self, wait_timeout_seconds: float) -> bool:
        # ... (Như trước) ...
        logger.info(f"Waiting up to {wait_timeout_seconds}s for consensus scores...")
        # ... (logic chờ và kiểm tra _has_sufficient_scores) ...
        if all_tasks_sufficient: logger.info("Sufficient scores received."); return True
        logger.warning("Consensus score waiting timed out.")
        return False

    # --- Phương thức mới để kiểm tra và phạt ---
    async def verify_and_penalize_validators(self):
        """
        Kiểm tra ValidatorDatum đã commit ở chu kỳ trước và áp dụng phạt nếu cần.
        Chạy ở đầu chu kỳ hiện tại.
        """
        logger.info(f"[V:{self.info.uid}] Verifying previous cycle ({self.current_cycle - 1}) validator updates...")
        previous_cycle = self.current_cycle - 1
        if previous_cycle < 0:
            logger.info("Skipping verification for the first cycle.")
            return

        # 1. Lấy dữ liệu thực tế on-chain của chu kỳ trước
        try:
            # Lấy tất cả ValidatorDatum MỚI NHẤT (giả sử có cách lọc theo chu kỳ commit hoặc lấy snapshot)
            on_chain_validator_data: List[ValidatorDatum] = await metagraph_data.get_all_validator_data(self.context)
            on_chain_states = {
                 datum.uid: {
                     "trust_score": getattr(datum, 'trust_score', 0) / 1_000_000.0,
                     "weight": getattr(datum, 'weight', 0) / 1_000_000.0,
                     "last_update_cycle": getattr(datum, 'last_update_cycle', -1)
                     # Thêm các trường cần kiểm tra khác (ví dụ: E_v nếu lưu)
                 } for datum in on_chain_validator_data if getattr(datum, 'last_update_cycle', -1) == previous_cycle
            }
            logger.info(f"Fetched {len(on_chain_states)} validator datums updated in cycle {previous_cycle}.")
        except Exception as e:
            logger.error(f"Failed to fetch on-chain validator data for verification: {e}")
            return

        # 2. Lấy kết quả tính toán mong đợi từ chu kỳ trước (đã lưu trong self.previous_cycle_results)
        expected_states = self.previous_cycle_results.get("calculated_validator_states", {})
        if not expected_states:
            logger.warning("No expected validator states found from previous cycle to verify against.")
            return

        penalized_validators: Set[str] = set()
        validator_penalty_updates: Dict[str, ValidatorDatum] = {}

        # 3. So sánh và xác định validator gian lận
        suspicious_validators: Dict[str, str] = {} # {uid: reason}
        for uid, expected in expected_states.items():
            if uid == self.info.uid: continue # Không tự kiểm tra mình ở bước này

            actual = on_chain_states.get(uid)
            if not actual:
                logger.warning(f"Validator {uid} did not commit updates in cycle {previous_cycle}.")
                # Có thể phạt nhẹ vì không cập nhật?
                continue

            # So sánh các trường quan trọng (ví dụ: trust score)
            diff_trust = abs(actual.get("trust_score", -1) - expected.get("trust", -1))
            # diff_weight = abs(actual.get("weight", -1) - expected.get("weight", -1))
            # ... so sánh các trường khác ...

            if diff_trust > self.param_datum_comparison_tolerance: # Sử dụng ngưỡng sai số
                reason = f"Trust mismatch (Expected: {expected.get('trust', -1):.5f}, Actual: {actual.get('trust_score', -1):.5f})"
                logger.warning(f"Potential fraud detected for Validator {uid}: {reason}")
                suspicious_validators[uid] = reason
            # Thêm kiểm tra cho các trường khác...

        # 4. Đồng thuận về Gian lận (Placeholder - Cần logic P2P phức tạp)
        confirmed_cheaters: Dict[str, str] = {}
        if suspicious_validators:
            logger.info("Requesting consensus on suspicious validators...")
            # --- Logic P2P để các validator bỏ phiếu/xác nhận gian lận ---
            # confirmed_cheaters = await self.request_fraud_consensus(suspicious_validators)
            # Giả lập: Coi tất cả nghi ngờ là đã xác nhận gian lận
            confirmed_cheaters = suspicious_validators
            logger.warning(f"Fraud confirmed (mock): {list(confirmed_cheaters.keys())}")


        # 5. Áp dụng Trừng phạt cho validator đã xác nhận gian lận
        for uid, reason in confirmed_cheaters.items():
            validator_info = self.validators_info.get(uid) # Lấy thông tin validator từ metagraph vừa load
            if not validator_info: continue

            logger.warning(f"Applying penalty to Validator {uid} for: {reason}")
            penalized_validators.add(uid)

            # Xác định mức độ nghiêm trọng (ví dụ: Bậc 3 cho gian lận datum)
            # fraud_severity = calculate_fraud_severity_value({"type": "Datum_Manipulation", ...})
            fraud_severity = 0.8 # Giả định mức độ cao

            # Tính toán Slashing
            slash_amount = calculate_slash_amount(validator_info.stake, fraud_severity, self.param_max_slash_rate)
            logger.warning(f"Calculated slash amount for {uid}: {slash_amount}")
            # --- Kích hoạt cơ chế Slashing thực tế (Tương tác Smart Contract) ---
            # await self.trigger_slashing(uid, slash_amount)

            # Phạt Trust Score (Giảm mạnh)
            penalty_factor = 1 - self.param_penalty_eta # eta ví dụ 0.5 -> giảm 50%
            new_trust_score = validator_info.trust_score * penalty_factor
            logger.warning(f"Penalizing Trust Score for {uid}: {validator_info.trust_score:.3f} -> {new_trust_score:.3f}")
            validator_info.trust_score = new_trust_score # Cập nhật trạng thái local

            # Chuẩn bị ValidatorDatum mới để commit hình phạt
            # Cần lấy Datum cũ/UTXO của validator này
            # old_val_datum = ...
            # new_val_datum = ValidatorDatum(
            #     uid=uid,
            #     trust_score=int(new_trust_score * 1_000_000),
            #     # ... cập nhật các trường khác, có thể thêm cờ 'penalized' ...
            #     last_update_cycle=self.current_cycle # Ghi nhận cập nhật ở chu kỳ này
            # )
            # validator_penalty_updates[uid] = new_val_datum

        # Commit các cập nhật phạt (nếu có) - Có thể gộp với commit cuối chu kỳ
        if validator_penalty_updates:
             logger.info("Committing validator penalty updates...")
             # await self.commit_updates_to_blockchain({}, validator_penalty_updates) # Chỉ commit validator updates

        # Cập nhật lại self.validators_info với trust score mới của người bị phạt
        # để ảnh hưởng đến chu kỳ hiện tại
        for uid in penalized_validators:
            if uid in self.validators_info: # Cập nhật lại từ dict nếu đã bị sửa đổi
                penalized_info = self.validators_info[uid]
                # Đảm bảo trust score đã được cập nhật trong dict
                logger.info(f"Validator {uid} trust score set to {penalized_info.trust_score:.3f} for current cycle.")


    def run_consensus_and_penalties(self) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        Thực hiện đồng thuận điểm miners, tính E_validator và chuẩn bị trạng thái validator mới.
        Trả về điểm miner cuối cùng và trạng thái validator dự kiến.
        """
        logger.info(f"[V:{self.info.uid}] Running consensus and calculating validator states...")
        final_miner_scores: Dict[str, float] = {}
        validator_avg_deviations: Dict[str, float] = defaultdict(float)
        validator_deviation_counts: Dict[str, int] = defaultdict(int)
        calculated_validator_states: Dict[str, Any] = {} # Lưu kết quả tính toán cho chu kỳ sau

        scores_this_cycle = self.received_validator_scores.get(self.current_cycle, {})
        scores_by_miner: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        tasks_processed_by_miner: Dict[str, str] = {}

        # --- 1. Đồng thuận điểm Miner (Tính P_miner_adjusted) ---
        for task_id, validator_scores_dict in scores_this_cycle.items():
            assignment = self.tasks_sent.get(task_id)
            if not assignment: continue
            miner_uid = assignment.miner_uid
            tasks_processed_by_miner[miner_uid] = task_id
            for validator_uid, score_entry in validator_scores_dict.items():
                validator = self.validators_info.get(validator_uid)
                if validator: scores_by_miner[miner_uid].append((score_entry.score, validator.trust_score))

        for miner_uid, scores_trusts in scores_by_miner.items():
            if not scores_trusts: continue
            scores = [s for s, t in scores_trusts]; trusts = [t for s, t in scores_trusts]
            p_adj = calculate_adjusted_miner_performance(scores, trusts)
            final_miner_scores[miner_uid] = p_adj
            logger.info(f"  Consensus score (P_adj) for Miner {miner_uid}: {p_adj:.3f}")

            # --- 2. Tính độ lệch ---
            task_id = tasks_processed_by_miner.get(miner_uid)
            if not task_id: continue
            for validator_uid, score_entry in scores_this_cycle.get(task_id, {}).items():
                 if score_entry.miner_uid == miner_uid:
                     deviation = abs(score_entry.score - p_adj)
                     validator_avg_deviations[validator_uid] += deviation
                     validator_deviation_counts[validator_uid] += 1
                     if validator_uid == self.info.uid:
                         for my_score in self.validator_scores.get(task_id, []):
                             if my_score.miner_uid == miner_uid: my_score.deviation = deviation; break

        for val_uid in validator_avg_deviations:
            count = validator_deviation_counts[val_uid]
            if count > 0: validator_avg_deviations[val_uid] /= count

        # --- 3. Tính E_validator và Trust mới cho Validator ---
        for validator_uid, validator_info in self.validators_info.items():
            avg_dev = validator_avg_deviations.get(validator_uid, 0.0)
            metric_quality_example = max(0.0, 1.0 - avg_dev * 1.5)
            q_task_val_example = 0.0
            new_e_validator = calculate_validator_performance(...) # Như trước
            logger.info(f"  Calculated performance (E_val) for Validator {validator_uid}: {new_e_validator:.3f}")

            # --- Cập nhật Trust Score Validator ---
            # Không áp dụng phạt ở bước này, chỉ tính toán trạng thái mới dự kiến
            time_since_val_eval = 1
            new_val_trust_score = update_trust_score(
                 validator_info.trust_score, time_since_val_eval, new_e_validator, # Dùng E_val mới
                 # ... các tham số trust update ...
            )
            logger.info(f"  Calculated next Trust for Validator {validator_uid}: {new_val_trust_score:.3f}")

            # --- Tính Weight mới cho Validator (nếu cần) ---
            # new_val_weight = calculate_validator_weight(...)

            # Lưu trạng thái dự kiến để kiểm tra ở chu kỳ sau
            calculated_validator_states[validator_uid] = {
                "E_v": new_e_validator,
                "trust": new_val_trust_score,
                # "weight": new_val_weight,
                "last_update_cycle": self.current_cycle # Ghi lại chu kỳ tính toán
            }

        return final_miner_scores, calculated_validator_states


    def update_miner_state(self, final_scores: Dict[str, float]) -> Dict[str, MinerDatum]:
        # ... (Như trước, trả về dict miner_updates) ...
        logger.info(f"[V:{self.info.uid}] Preparing miner state updates...")
        miner_updates: Dict[str, MinerDatum] = {}
        # ... (logic tính toán new_trust, new_weight, incentive) ...
        logger.info(f"  Prepared update for Miner {miner_uid}: Trust={new_trust_score:.3f}, Weight={new_weight:.3f}, Incentive={incentive:.4f}")
        # Tạo MinerDatum mới...
        # miner_updates[miner_uid] = new_datum
        return miner_updates

    def prepare_validator_updates(self, calculated_states: Dict[str, Any]) -> Dict[str, ValidatorDatum]:
        """Chuẩn bị dữ liệu ValidatorDatum để commit dựa trên trạng thái đã tính toán."""
        logger.info(f"[V:{self.info.uid}] Preparing validator state updates...")
        validator_updates: Dict[str, ValidatorDatum] = {}
        for validator_uid, state in calculated_states.items():
             # Chỉ chuẩn bị update cho chính mình hoặc theo logic khác?
             # if validator_uid == self.info.uid:
                 # Cần lấy Datum cũ
                 # new_datum = ValidatorDatum(
                 #     uid=validator_uid,
                 #     trust_score=int(state.get("trust", 0) * 1_000_000),
                 #     # weight=int(state.get("weight", 0) * 1_000_000),
                 #     last_update_cycle=state.get("last_update_cycle", self.current_cycle),
                 #     # ... các trường khác ...
                 # )
                 # validator_updates[validator_uid] = new_datum
                 logger.debug(f"  Prepared update for Validator {validator_uid}")
        return validator_updates

    async def commit_updates_to_blockchain(self, miner_updates: Dict[str, MinerDatum], validator_updates: Dict[str, ValidatorDatum]):
        """Gửi giao dịch cập nhật Datum lên blockchain (async)."""
        logger.info("Committing updates to blockchain...")
        tasks = []

        # --- Cập nhật Miner Datums ---
        logger.info(f"  Preparing to commit {len(miner_updates)} Miner datums.")
        for miner_uid, new_datum in miner_updates.items():
             # miner_utxo = await metagraph_data.find_miner_utxo(self.context, miner_uid)
             # if miner_utxo: tasks.append(update_metagraph.update_miner_datum(...))
             # else: logger.error(...)
             await asyncio.sleep(0.01) # Mock

        # --- Cập nhật Validator Datums ---
        logger.info(f"  Preparing to commit {len(validator_updates)} Validator datums.")
        for validator_uid, new_datum in validator_updates.items():
             # validator_utxo = await metagraph_data.find_validator_utxo(self.context, validator_uid)
             # if validator_utxo: tasks.append(update_metagraph.update_validator_datum(...))
             # else: logger.error(...)
             await asyncio.sleep(0.01) # Mock

        # --- Gửi tất cả các giao dịch cập nhật ---
        if tasks:
            logger.info(f"Sending {len(tasks)} update transactions...")
            # results = await asyncio.gather(*tasks, return_exceptions=True)
            # Xử lý results...
            logger.info("Datum update transactions sent.")
        else:
             logger.info("  No actual updates to commit in mock.")


    async def run_cycle(self):
        """Thực hiện một chu kỳ đồng thuận hoàn chỉnh (async)."""
        logger.info(f"\n--- Starting Cycle {self.current_cycle} for Validator {self.info.uid} ---")
        cycle_start_time = time.time()
        metagraph_update_time = cycle_start_time + METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
        send_score_time = metagraph_update_time - SEND_SCORE_OFFSET_MINUTES * 60
        consensus_timeout_time = metagraph_update_time - CONSENSUS_TIMEOUT_OFFSET_MINUTES * 60
        commit_time = metagraph_update_time - 15 # Commit trước 15 giây

        miner_updates: Dict[str, MinerDatum] = {}
        validator_updates: Dict[str, ValidatorDatum] = {}

        try:
            # *** Bước 0: Kiểm tra và phạt Validator từ chu kỳ TRƯỚC ***
            await self.verify_and_penalize_validators()

            # 1. Tải dữ liệu (bao gồm trạng thái đã bị phạt nếu có)
            await self.load_metagraph_data()
            if not self.miners_info: raise Exception("No miners found")

            # 2. Chọn miners
            selected_miners = await self.select_miners()
            if not selected_miners: raise Exception("No miners selected")

            # 3. Gửi task
            await self.send_task_and_track(selected_miners)

            # 4. Nhận kết quả
            receive_timeout = 30.0
            await self.receive_results(timeout=receive_timeout)

            # 5. Chấm điểm cục bộ
            self.score_miner_results()

            # 6. Chờ và gửi điểm
            wait_before_send = send_score_time - time.time()
            if wait_before_send > 0:
                logger.info(f"Waiting {wait_before_send:.1f}s before broadcasting scores...")
                await asyncio.sleep(wait_before_send)
            await self.broadcast_scores()

            # 7. Chờ nhận điểm
            wait_for_scores_timeout = consensus_timeout_time - time.time()
            consensus_possible = False
            if wait_for_scores_timeout > 0:
                 consensus_possible = await self.wait_for_consensus_scores(wait_for_scores_timeout)
            else:
                 logger.warning("Not enough time left to wait for consensus scores.")

            # 8. Chạy đồng thuận, tính toán trạng thái mới (KHÔNG phạt ở đây)
            final_miner_scores, calculated_validator_states = self.run_consensus_and_penalties()
            if not consensus_possible:
                 logger.warning("Consensus calculated with potentially incomplete score set.")

            # Lưu kết quả tính toán validator cho chu kỳ sau kiểm tra
            self.previous_cycle_results["calculated_validator_states"] = calculated_validator_states
            self.previous_cycle_results["final_miner_scores"] = final_miner_scores # Lưu cả điểm miner nếu cần

            # 9. Chuẩn bị cập nhật trạng thái miner
            miner_updates = self.update_miner_state(final_miner_scores)

            # 10. Chuẩn bị cập nhật trạng thái validator (dựa trên kết quả tính toán)
            validator_updates = self.prepare_validator_updates(calculated_validator_states)

            # 11. Chờ commit
            wait_before_commit = commit_time - time.time()
            if wait_before_commit > 0:
                 logger.info(f"Waiting {wait_before_commit:.1f}s before committing updates...")
                 await asyncio.sleep(wait_before_commit)

            # 12. Commit lên blockchain
            await self.commit_updates_to_blockchain(miner_updates, validator_updates)

        except Exception as e:
            logger.exception(f"Error during cycle {self.current_cycle}: {e}")

        finally:
            cycle_end_time = time.time()
            logger.info(f"--- Cycle {self.current_cycle} Finished (Duration: {cycle_end_time - cycle_start_time:.1f}s) ---")
            self.current_cycle += 1
            # Dọn dẹp dữ liệu chu kỳ cũ
            cleanup_cycle = self.current_cycle - 3
            async with self.received_scores_lock:
                 if cleanup_cycle in self.received_validator_scores:
                      del self.received_validator_scores[cleanup_cycle]
                      logger.info(f"Cleaned up received scores for cycle {cleanup_cycle}")


# --- Hàm chạy chính (Ví dụ Async) ---
async def main_validator_loop():
    # ... (Khởi tạo như cũ) ...
    my_validator_info = ValidatorInfo(uid="V1", address="addr_v1", api_endpoint="http://127.0.0.1:8001", trust_score=0.9, weight=1.5, stake=1000)
    validator_node = ValidatorNode(my_validator_info, cardano_context=None, config=None)

    # --- Chạy FastAPI app (Ví dụ đơn giản) ---
    # Cần chạy trong một tiến trình hoặc luồng riêng biệt trong thực tế
    # Hoặc tích hợp vào event loop nếu FastAPI hỗ trợ tốt
    # try:
    #     from sdk.consensus.api import set_validator_node_instance
    #     set_validator_node_instance(validator_node) # Inject instance
    #     print("Validator node instance injected into API.")
    # except Exception as e:
    #     print(f"Could not inject validator node into API: {e}")

    # Chạy các chu kỳ đồng thuận
    try:
        while True:
            cycle_start_time = time.time()
            await validator_node.run_cycle()
            cycle_duration = time.time() - cycle_start_time
            cycle_interval_seconds = METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
            wait_time = max(10, cycle_interval_seconds - cycle_duration) # Đợi ít nhất 10s
            print(f"Cycle duration: {cycle_duration:.1f}s. Waiting {wait_time:.1f}s for next cycle...")
            await asyncio.sleep(wait_time)
    except asyncio.CancelledError:
        print("Validator node stopping...")
    finally:
        await validator_node.http_client.aclose()
        print("Validator node stopped.")

if __name__ == "__main__":
    try:
        print("Starting validator node loop...")
        asyncio.run(main_validator_loop())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

