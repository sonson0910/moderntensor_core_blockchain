# sdk/consensus/scoring.py
"""
Logic chấm điểm kết quả từ miners.
"""
import logging
from typing import List, Dict, Any

try:
    from sdk.core.datatypes import MinerResult, TaskAssignment, ValidatorScore
except ImportError as e:
    raise ImportError(f"Error importing dependencies in scoring.py: {e}")

logger = logging.getLogger(__name__)

def _calculate_score_from_result(task_data: Any, result_data: Any) -> float:
    """
    Tính điểm P_miner,v từ dữ liệu task và kết quả.
    *** Cần logic chấm điểm thực tế dựa trên loại task AI ***
    """
    # TODO: Triển khai logic chấm điểm thực tế.
    # Ví dụ đơn giản dựa trên loss:
    score = 0.0
    try:
        loss = float(result_data.get("loss", 1.0))
        score = max(0.0, min(1.0, 1.0 - loss * 1.2)) # Điều chỉnh hệ số
        logger.debug(f"Calculated score based on loss {loss:.4f}: {score:.3f}")
    except (TypeError, ValueError) as e:
        score = 0.1 # Phạt nhẹ nếu format sai
        logger.warning(f"Could not parse loss from result data {str(result_data)[:50]}... : {e}. Assigning low score.")
    except Exception as e:
        logger.exception(f"Unexpected error calculating score from result: {e}. Assigning low score.")
        score = 0.1
    return score

def score_results_logic(
    results_received: Dict[str, List[MinerResult]],
    tasks_sent: Dict[str, TaskAssignment],
    validator_uid: str
) -> Dict[str, List[ValidatorScore]]:
    """
    Chấm điểm tất cả các kết quả hợp lệ nhận được từ miners.

    Args:
        results_received: Dictionary kết quả nhận được {task_id: [MinerResult]}.
        tasks_sent: Dictionary các task đã gửi {task_id: TaskAssignment}.
        validator_uid: UID của validator đang thực hiện chấm điểm.

    Returns:
        Dictionary điểm số đã chấm {task_id: [ValidatorScore]}.
    """
    logger.info(f"[V:{validator_uid}] Scoring {len(results_received)} received tasks...")
    validator_scores: Dict[str, List[ValidatorScore]] = {}

    for task_id, results in results_received.items():
        assignment = tasks_sent.get(task_id)
        if not assignment:
            logger.warning(f"Received result for unknown/unsent task {task_id}. Skipping scoring.")
            continue

        if task_id not in validator_scores:
            validator_scores[task_id] = []

        for result in results:
            # Kiểm tra xem miner có đúng là miner được giao task không
            if result.miner_uid != assignment.miner_uid:
                 logger.warning(f"Received result for task {task_id} from unexpected miner {result.miner_uid}. Expected {assignment.miner_uid}. Skipping.")
                 continue

            score = _calculate_score_from_result(assignment.task_data, result.result_data)
            logger.info(f"  Scored Miner {result.miner_uid} for task {task_id}: {score:.3f}")

            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=result.miner_uid,
                validator_uid=validator_uid,
                score=score # Điểm P_miner,v
                # timestamp được tự động gán khi tạo ValidatorScore
            )
            validator_scores[task_id].append(val_score)

    logger.info(f"Finished scoring. Generated scores for {len(validator_scores)} tasks.")
    return validator_scores

