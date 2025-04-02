from sdk.formulas.dao import calculate_voting_power

def test_calculate_voting_power():
    stake = 1000.0
    time_staked = 5
    total_time = 10
    expected_power = 1000 * (1 + 5 / 10)  # 1500.0
    result = calculate_voting_power(stake, time_staked, total_time)
    assert result == expected_power, "Quyền biểu quyết tính không đúng"