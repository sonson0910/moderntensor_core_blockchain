# sdk/moderntensor_formulas/tests/test_incentive.py
import pytest
from sdk.formulas.incentive import calculate_miner_incentive, calculate_validator_incentive

def test_calculate_miner_incentive():
    # Input
    trust_score = 0.9
    miner_weight = 2.0
    performance_scores = [0.8, 0.9, 0.7]
    total_system_value = 50.0
    # Công thức: trust_score * (miner_weight * sum(performance_scores) / total_system_value)
    expected_incentive = 0.9 * (2.0 * (0.8 + 0.9 + 0.7) / 50.0)
    result = calculate_miner_incentive(trust_score, miner_weight, performance_scores, total_system_value)
    assert result == pytest.approx(expected_incentive, rel=1e-5), "Kết quả tính incentive cho miner không đúng"

def test_calculate_validator_incentive():
    # Input
    trust_score = 0.85
    validator_weight = 3.0
    validator_performance = 0.95
    total_validator_value = 60.0
    # Công thức: trust_score * (validator_weight * validator_performance / total_validator_value)
    expected_incentive = 0.85 * (3.0 * 0.95 / 60.0)
    result = calculate_validator_incentive(trust_score, validator_weight, validator_performance, total_validator_value)
    assert result == pytest.approx(expected_incentive, rel=1e-5), "Kết quả tính incentive cho validator không đúng"