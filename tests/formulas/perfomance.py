# sdk/moderntensor_formulas/tests/test_performance.py
import pytest
import math
from sdk.formulas.performance import calculate_task_completion_rate, calculate_adjusted_miner_performance

def test_calculate_task_completion_rate():
    # Input
    success_tasks = [8, 9, 10]
    total_tasks = [10, 10, 10]
    current_time = 3
    decay_constant = 0.5
    # Công thức: sum(success_tasks[i] * exp(-decay_constant * (current_time - i))) / sum(total_tasks[i] * exp(-decay_constant * (current_time - i)))
    numerator = 8 * math.exp(-0.5 * 2) + 9 * math.exp(-0.5 * 1) + 10 * math.exp(-0.5 * 0)
    denominator = 10 * math.exp(-0.5 * 2) + 10 * math.exp(-0.5 * 1) + 10 * math.exp(-0.5 * 0)
    expected_rate = numerator / denominator
    result = calculate_task_completion_rate(success_tasks, total_tasks, current_time, decay_constant)
    assert result == pytest.approx(expected_rate, rel=1e-5), "Tỷ lệ hoàn thành task tính không đúng"

def test_calculate_adjusted_miner_performance():
    # Input
    trust_scores = [0.8, 0.5]
    performance_scores = [0.9, 0.7]
    # Công thức: sum(trust_scores[i] * performance_scores[i]) / sum(trust_scores)
    expected_performance = (0.8 * 0.9 + 0.5 * 0.7) / (0.8 + 0.5)
    result = calculate_adjusted_miner_performance(trust_scores, performance_scores)
    assert result == pytest.approx(expected_performance, rel=1e-5), "Hiệu suất điều chỉnh của miner tính không đúng"