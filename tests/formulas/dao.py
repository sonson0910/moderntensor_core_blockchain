# sdk/moderntensor_formulas/tests/test_dao.py
import pytest
from ..dao import calculate_voting_power

def test_calculate_voting_power():
    # Input
    stake = 1000.0
    time_staked = 5
    total_time = 10
    # Công thức: stake * (1 + time_staked / total_time)
    expected_power = 1000 * (1 + 5 / 10)
    result = calculate_voting_power(stake, time_staked, total_time)
    assert result == expected_power, "Quyền biểu quyết tính không đúng"