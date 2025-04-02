# sdk/moderntensor_formulas/tests/test_penalty.py
import pytest
from ..penalty import calculate_performance_adjustment, calculate_slash_amount

def test_calculate_performance_adjustment():
    # Input
    performance_score = 0.8
    penalty_factor = 0.1
    # Công thức: performance_score * (1 - penalty_factor)
    expected_adjustment = 0.8 * (1 - 0.1)
    result = calculate_performance_adjustment(performance_score, penalty_factor)
    assert result == pytest.approx(expected_adjustment, rel=1e-5), "Điều chỉnh hiệu suất không đúng"

def test_calculate_slash_amount():
    # Input
    stake = 1000.0
    fraud_severity = 0.15
    max_slash_rate = 0.2
    # Công thức: min(max_slash_rate * stake, fraud_severity * stake)
    expected_slash = min(0.2 * 1000, 0.15 * 1000)
    result = calculate_slash_amount(stake, fraud_severity, max_slash_rate)
    assert result == expected_slash, "Số tiền phạt tính không đúng"