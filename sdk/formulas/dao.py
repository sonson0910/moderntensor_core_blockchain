# sdk/moderntensor_formulas/dao.py

def calculate_voting_power(
    stake: float,
    participation_score: float,
    total_stake: float
) -> float:
    """
    Tính quyền biểu quyết trong DAO dựa trên stake và mức độ tham gia.

    Args:
        stake (float): Số tiền stake của thành viên.
        participation_score (float): Điểm tham gia của thành viên.
        total_stake (float): Tổng số tiền stake trong DAO.

    Returns:
        float: Quyền biểu quyết của thành viên.
    """
    voting_power = (stake / total_stake) * participation_score if total_stake != 0 else 0.0
    return max(0.0, voting_power)