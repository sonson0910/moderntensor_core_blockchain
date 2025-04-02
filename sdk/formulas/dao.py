# sdk/formulas/dao.py

def calculate_voting_power(stake: float, time_staked: float, total_time: float) -> float:
    """
    Tính quyền biểu quyết trong DAO dựa trên stake và thời gian stake.
    
    Args:
        stake (float): Số tiền stake của thành viên.
        time_staked (float): Thời gian stake của thành viên.
        total_time (float): Thời gian tổng để chuẩn hóa.
    
    Returns:
        float: Quyền biểu quyết của thành viên.
    """
    if total_time == 0:
        return stake  # Tránh chia cho 0, quyền biểu quyết chỉ dựa trên stake
    voting_power = stake * (1 + time_staked / total_time)
    return max(0.0, voting_power)