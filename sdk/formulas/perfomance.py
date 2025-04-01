# sdk/moderntensor_formulas/performance.py
import math
from typing import List

def calculate_task_completion_rate(
    success_tasks: List[int],
    total_tasks: List[int],
    current_time: int,
    decay_constant: float = 0.5
) -> float:
    """
    Tính tỷ lệ hoàn thành nhiệm vụ với yếu tố suy giảm theo thời gian.

    Args:
        success_tasks (List[int]): Danh sách nhiệm vụ hoàn thành thành công theo thời gian.
        total_tasks (List[int]): Danh sách tổng số nhiệm vụ theo thời gian.
        current_time (int): Thời điểm hiện tại.
        decay_constant (float): Hằng số suy giảm cho các nhiệm vụ cũ.

    Returns:
        float: Tỷ lệ hoàn thành nhiệm vụ.
    """
    numerator = sum(success * math.exp(-decay_constant * (current_time - t))
                    for t, success in enumerate(success_tasks))
    denominator = sum(total * math.exp(-decay_constant * (current_time - t))
                      for t, total in enumerate(total_tasks))
    return numerator / denominator if denominator != 0 else 0.0

def calculate_adjusted_miner_performance(
    trust_scores: List[float],
    performance_scores: List[float]
) -> float:
    """
    Tính hiệu suất điều chỉnh của miner dựa trên điểm tin cậy của validators.

    Args:
        trust_scores (List[float]): Điểm tin cậy của các validators.
        performance_scores (List[float]): Điểm hiệu suất do validators đưa ra.

    Returns:
        float: Điểm hiệu suất điều chỉnh.
    """
    numerator = sum(trust * perf for trust, perf in zip(trust_scores, performance_scores))
    total_trust = sum(trust_scores)
    return numerator / total_trust if total_trust != 0 else 0.0