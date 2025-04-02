# sdk/moderntensor_formulas/trust_score.py
import math

def update_trust_score(
    old_trust_score: float,
    time_since_last_eval: int,
    new_score: float,
    decay_constant: float = 0.1,
    learning_rate: float = 0.1
) -> float:
    """
    Cập nhật điểm tin cậy với yếu tố suy giảm do không hoạt động.

    Args:
        old_trust_score (float): Điểm tin cậy trước đó.
        time_since_last_eval (int): Thời gian kể từ lần đánh giá cuối cùng.
        new_score (float): Điểm hiệu suất mới.
        decay_constant (float): Hằng số suy giảm.
        learning_rate (float): Tỷ lệ học để cập nhật điểm.

    Returns:
        float: Điểm tin cậy đã cập nhật.
    """
    decayed_score = old_trust_score * math.exp(-decay_constant * time_since_last_eval)
    updated_score = decayed_score + learning_rate * new_score
    return max(0.0, min(1.0, updated_score))  # Giới hạn trong khoảng [0, 1]

def calculate_selection_probability(
    trust_score: float,
    time_since_last_selection: int,
    bonus_factor: float = 0.2
) -> float:
    """
    Tính xác suất chọn miner dựa trên điểm tin cậy và thời gian không được chọn.

    Args:
        trust_score (float): Điểm tin cậy của miner.
        time_since_last_selection (int): Thời gian kể từ lần chọn cuối cùng.
        bonus_factor (float): Hệ số thưởng để đảm bảo công bằng.

    Returns:
        float: Xác suất chọn miner.
    """
    probability = trust_score * (1 + bonus_factor * time_since_last_selection)
    return max(0.0, probability)