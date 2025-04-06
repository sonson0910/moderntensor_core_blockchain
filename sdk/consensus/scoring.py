# sdk/consensus/scoring.py
"""
Logic chấm điểm kết quả từ miners.
Chứa hàm cơ sở cần được kế thừa và triển khai bởi các validator/subnet cụ thể.
"""
import logging
from typing import List, Dict, Any
from collections import defaultdict
# Giả định các kiểu dữ liệu này đã được import hoặc định nghĩa đúng
try:
    from sdk.core.datatypes import MinerResult, TaskAssignment, ValidatorScore
except ImportError as e:
    raise ImportError(f"Error importing dependencies in scoring.py: {e}")

logger = logging.getLogger(__name__)

def _calculate_score_from_result(task_data: Any, result_data: Any) -> float:
    """
    (Cần được Override) Tính điểm P_miner,v từ dữ liệu task và kết quả.

    Đây là phương thức cơ sở/trừu tượng. Các lớp Validator kế thừa hoặc
    các cấu hình Subnet cụ thể cần triển khai (override) phương thức này
    với logic chấm điểm phù hợp cho loại nhiệm vụ AI của họ.

    Args:
        task_data: Dữ liệu của nhiệm vụ đã giao.
        result_data: Dữ liệu kết quả mà miner trả về.

    Returns:
        Điểm số (từ 0.0 đến 1.0).

    Raises:
        NotImplementedError: Nếu phương thức này không được override bởi lớp con.
    """
    logger.warning(
        f"'_calculate_score_from_result' is using the base implementation. "
        f"This should be overridden by specific subnet/validator logic. "
        f"Task data type: {type(task_data)}, Result data type: {type(result_data)}. "
        f"Returning default score 0.0"
    )
    # Hoặc bạn có thể raise lỗi để bắt buộc phải override:
    # raise NotImplementedError("Scoring logic must be implemented by validator subclass/subnet.")
    # Tạm thời trả về 0.0 để khung sườn chạy được
    return 0.0

def score_results_logic(
    results_received: Dict[str, List[MinerResult]],
    tasks_sent: Dict[str, TaskAssignment],
    validator_uid: str,
    # Thêm tham số để truyền hàm chấm điểm tùy chỉnh nếu không dùng kế thừa
    # scoring_function: Callable[[Any, Any], float] = _calculate_score_from_result
) -> Dict[str, List[ValidatorScore]]:
    """
    Chấm điểm tất cả các kết quả hợp lệ nhận được từ miners bằng cách sử dụng
    hàm chấm điểm _calculate_score_from_result (cần được override).

    Args:
        results_received: Dictionary kết quả nhận được {task_id: [MinerResult]}.
        tasks_sent: Dictionary các task đã gửi {task_id: TaskAssignment}.
        validator_uid: UID của validator đang thực hiện chấm điểm.
        # scoring_function: Hàm sẽ được dùng để tính điểm.

    Returns:
        Dictionary điểm số đã chấm {task_id: [ValidatorScore]}.
    """
    logger.info(f"[V:{validator_uid}] Scoring {len(results_received)} received tasks using defined logic...")
    validator_scores: Dict[str, List[ValidatorScore]] = defaultdict(list) # Dùng defaultdict

    for task_id, results in results_received.items():
        assignment = tasks_sent.get(task_id)
        if not assignment:
            logger.warning(f"Received result for unknown/unsent task {task_id}. Skipping scoring.")
            continue

        for result in results:
            if result.miner_uid != assignment.miner_uid:
                 logger.warning(f"Received result for task {task_id} from unexpected miner {result.miner_uid}. Expected {assignment.miner_uid}. Skipping.")
                 continue

            # Gọi hàm chấm điểm (có thể là hàm đã override)
            try:
                # score = scoring_function(assignment.task_data, result.result_data)
                score = _calculate_score_from_result(assignment.task_data, result.result_data)
                # Đảm bảo điểm nằm trong khoảng [0, 1]
                score = max(0.0, min(1.0, score))
            except NotImplementedError:
                 logger.error(f"Scoring logic for task type in task {task_id} is not implemented! Assigning score 0.")
                 score = 0.0
            except Exception as e:
                 logger.exception(f"Error calculating score for task {task_id}, miner {result.miner_uid}: {e}. Assigning score 0.")
                 score = 0.0

            logger.info(f"  Scored Miner {result.miner_uid} for task {task_id}: {score:.3f}")

            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=result.miner_uid,
                validator_uid=validator_uid,
                score=score # Điểm P_miner,v
            )
            validator_scores[task_id].append(val_score)

    logger.info(f"Finished scoring. Generated scores for {len(validator_scores)} tasks.")
    return dict(validator_scores) # Trả về dict thường

