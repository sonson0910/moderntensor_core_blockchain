# sdk/moderntensor_formulas/tests/test_trust_score.py
import pytest
import math
from sdk.formulas.trust_score import update_trust_score, calculate_selection_probability

def test_update_trust_score():
    # Input
    old_trust_score = 0.5
    time_since_last_eval = 2
    new_score = 0.0
    decay_constant = 0.1
    learning_rate = 0.1
    # Công thức: old_trust_score * exp(-decay_constant * time_since_last_eval) + learning_rate * new_score
    expected_score = 0.5 * math.exp(-0.1 * 2) + 0.1 * 0.0
    result = update_trust_score(old_trust_score, time_since_last_eval, new_score, decay_constant, learning_rate)
    assert result == pytest.approx(expected_score, rel=1e-5), "Điểm tin cậy cập nhật không đúng"

def test_calculate_selection_probability():
    # Input
    trust_score = 0.409
    time_since_last_selection = 2
    bonus_factor = 0.2
    # Công thức: trust_score * (1 + bonus_factor * time_since_last_selection)
    expected_probability = 0.409 * (1 + 0.2 * 2)
    result = calculate_selection_probability(trust_score, time_since_last_selection, bonus_factor)
    assert result == pytest.approx(expected_probability, rel=1e-5), "Xác suất chọn không đúng"