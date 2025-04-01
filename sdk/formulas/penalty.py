# sdk/moderntensor_formulas/penalty.py

def calculate_performance_adjustment(
    performance_score: float,
    penalty_factor: float = 0.1
) -> float:
    """
    Điều chỉnh hiệu suất dựa trên hình phạt.

    Args:
        performance_score (float): Điểm hiệu suất hiện tại.
        penalty_factor (float): Hệ số hình phạt.

    Returns:
        float: Điểm hiệu suất sau khi điều chỉnh.
    """
    adjustment = performance_score * (1 - penalty_factor)
    return max(0.0, adjustment)

def calculate_slash_amount(
    stake: float,
    fraud_severity: float,
    max_slash_rate: float = 0.5
) -> float:
    """
    Tính số tiền bị cắt (slash) dựa trên mức độ gian lận.

    Args:
        stake (float): Số tiền stake của miner/validator.
        fraud_severity (float): Mức độ nghiêm trọng của gian lận (0 đến 1).
        max_slash_rate (float): Tỷ lệ cắt tối đa.

    Returns:
        float: Số tiền bị cắt.
    """
    slash_amount = stake * min(max_slash_rate, fraud_severity)
    return max(0.0, slash_amount)