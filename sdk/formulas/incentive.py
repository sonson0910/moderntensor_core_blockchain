# sdk/moderntensor_formulas/incentive.py
from typing import List

def calculate_miner_incentive(
    trust_score: float,
    miner_weight: float,
    miner_performance_scores: List[float],
    total_system_value: float
) -> float:
    """
    Tính phần thưởng cho miner dựa trên điểm tin cậy, trọng số và điểm hiệu suất.

    Args:
        trust_score (float): Điểm tin cậy của miner.
        miner_weight (float): Trọng số của miner.
        miner_performance_scores (List[float]): Danh sách điểm hiệu suất từ validators.
        total_system_value (float): Tổng giá trị hệ thống để chuẩn hóa.

    Returns:
        float: Phần thưởng tính được cho miner.
    """
    sum_weighted_performance = miner_weight * sum(miner_performance_scores)
    incentive = trust_score * (sum_weighted_performance / total_system_value)
    return max(0.0, incentive)  # Đảm bảo phần thưởng không âm

def calculate_validator_incentive(
    trust_score: float,
    validator_weight: float,
    validator_performance: float,
    total_validator_value: float
) -> float:
    """
    Tính phần thưởng cho validator dựa trên điểm tin cậy, trọng số và hiệu suất.

    Args:
        trust_score (float): Điểm tin cậy của validator.
        validator_weight (float): Trọng số của validator.
        validator_performance (float): Điểm hiệu suất của validator.
        total_validator_value (float): Tổng giá trị của tất cả validators.

    Returns:
        float: Phần thưởng tính được cho validator.
    """
    weighted_performance = validator_weight * validator_performance
    incentive = trust_score * (weighted_performance / total_validator_value)
    return max(0.0, incentive)  # Đảm bảo phần thưởng không âm