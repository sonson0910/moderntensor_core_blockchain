# sdk/moderntensor_formulas/validator_weight.py

def calculate_validator_weight(
    stake: float,
    performance_score: float,
    total_stake: float
) -> float:
    """
    Tính trọng số của validator dựa trên stake và hiệu suất.

    Args:
        stake (float): Số tiền stake của validator.
        performance_score (float): Điểm hiệu suất của validator.
        total_stake (float): Tổng số tiền stake trong hệ thống.

    Returns:
        float: Trọng số của validator.
    """
    weight = (stake / total_stake) * performance_score if total_stake != 0 else 0.0
    return max(0.0, weight)