# sdk/moderntensor_formulas/tests/test_validator_weight.py
import pytest
from sdk.formulas.validator_weight import calculate_validator_weight

def test_calculate_validator_weight():
    # Input
    stake = 500.0
    performance_score = 0.9
    total_stake = 2000.0
    # Công thức: (stake / total_stake) * performance_score
    expected_weight = (500 / 2000) * 0.9
    result = calculate_validator_weight(stake, performance_score, total_stake)
    assert result == pytest.approx(expected_weight, rel=1e-5), "Trọng số validator tính không đúng"