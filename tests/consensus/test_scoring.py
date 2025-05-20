# tests/consensus/test_scoring.py
import pytest
import time
import copy
import dataclasses
from typing import Dict, List, Any, Tuple, Optional
from unittest.mock import (
    MagicMock,
    call,
    AsyncMock,
)  # Keep MagicMock if needed elsewhere, add AsyncMock if patching async
from pytest_mock import MockerFixture  # Import MockerFixture

# Import components
# Assume _calculate_score_from_result is defined/imported in scoring.py
from sdk.consensus.scoring import score_results_logic, _calculate_score_from_result
from sdk.core.datatypes import MinerResult, TaskAssignment, ValidatorScore

# --- Fixtures ---


@pytest.fixture
def validator_uid() -> str:
    return "validator_score_test_hex"


@pytest.fixture
def sample_tasks_sent(validator_uid: str) -> Dict[str, TaskAssignment]:
    """Tạo dictionary các task đã gửi mẫu."""
    ts = time.time()
    task1 = TaskAssignment(
        task_id="task_s01",
        miner_uid="miner_S_A_hex",
        task_data={"input": 1},
        validator_uid=validator_uid,
        timestamp_sent=ts,
        expected_result_format=dict,
    )
    time.sleep(0.01)
    ts = time.time()
    task2 = TaskAssignment(
        task_id="task_s02",
        miner_uid="miner_S_B_hex",
        task_data={"input": 2},
        validator_uid=validator_uid,
        timestamp_sent=ts,
        expected_result_format=dict,
    )
    time.sleep(0.01)
    ts = time.time()
    task3 = TaskAssignment(
        task_id="task_s03",
        miner_uid="miner_S_A_hex",
        task_data={"input": 3},
        validator_uid=validator_uid,
        timestamp_sent=ts,
        expected_result_format=dict,
    )
    return {task1.task_id: task1, task2.task_id: task2, task3.task_id: task3}


# --- UPDATED Fixture ---
@pytest.fixture
def sample_results_received_dict(
    sample_tasks_sent: Dict[str, TaskAssignment],
) -> Dict[str, List[MinerResult]]:
    """Tạo dict các kết quả nhận được mẫu, nhóm theo task_id."""
    task1 = sample_tasks_sent["task_s01"]
    task2 = sample_tasks_sent["task_s02"]
    res1 = MinerResult(
        task_id=task1.task_id,
        miner_uid=task1.miner_uid,
        result_data={"output": 10},
        timestamp_received=time.time() + 0.1,
    )
    time.sleep(0.01)
    res2 = MinerResult(
        task_id=task2.task_id,
        miner_uid=task2.miner_uid,
        result_data={"output": 20},
        timestamp_received=time.time() + 0.1,
    )
    res_unmatched = MinerResult(
        task_id="task_s99",
        miner_uid="miner_S_C_hex",
        result_data={"output": 99},
        timestamp_received=time.time() + 0.2,
    )  # This won't be in the dict keys usually
    res1_duplicate = MinerResult(
        task_id=task1.task_id,
        miner_uid=task1.miner_uid,
        result_data={"output": 11},
        timestamp_received=time.time() + 0.3,
    )
    # Result from wrong miner for task 2
    res2_wrong_miner = MinerResult(
        task_id=task2.task_id,
        miner_uid="miner_WRONG_hex",
        result_data={"output": 22},
        timestamp_received=time.time() + 0.4,
    )

    results_dict = {}
    # Group by task_id
    results_dict[res1.task_id] = [res1, res1_duplicate]  # task_s01 has two results
    results_dict[res2.task_id] = [
        res2,
        res2_wrong_miner,
    ]  # task_s02 has two results (one wrong miner)
    # res_unmatched won't be added as no corresponding task_id in sample_tasks_sent
    # If the input to score_results_logic assumes all keys exist, need to handle that.
    # Based on the function code, it iterates the dict, so only keys present matter.
    return results_dict


# --- END UPDATED Fixture ---

# --- Test Cases ---


def test_score_results_logic_basic(
    mocker: MockerFixture,
    validator_uid: str,
    sample_results_received_dict: Dict[str, List[MinerResult]],
    sample_tasks_sent: Dict[str, TaskAssignment],
):
    """Tests basic scoring flow with matching tasks and results."""
    # Setup mock scores for specific tasks using side_effect on the patched function
    expected_score1 = 0.95
    expected_score2 = 0.88
    mock_scores = {"task_s01": expected_score1, "task_s02": expected_score2}

    def score_side_effect(task_data, result_data):
        # Simulate scoring based on task input or result output if needed
        # For now, just return predefined scores based on task_id derived from task_data (if possible)
        # Or more simply, just use a list side_effect if order is predictable
        # Here, we rely on the order of iteration in the function being tested
        # A safer way might involve inspecting args inside side_effect
        if task_data == sample_tasks_sent["task_s01"].task_data:
            return expected_score1
        if task_data == sample_tasks_sent["task_s02"].task_data:
            return expected_score2
        return 0.5  # Default

    # Patch the FUNCTION directly within the module where it's called from
    mock_calculate_score = mocker.patch(
        "sdk.consensus.scoring._calculate_score_from_result",
        side_effect=score_side_effect,
        # return_value=0.9 # simpler alternative
    )

    # Execute the function (remove subclass_instance)
    validator_scores = score_results_logic(
        validator_uid=validator_uid,  # Pass correct arg name
        results_received=sample_results_received_dict,
        tasks_sent=sample_tasks_sent,
    )

    # Assertions
    assert isinstance(validator_scores, dict)
    # Checks only first valid result per task_id
    assert len(validator_scores) == 2  # Should score task_s01 and task_s02

    # Kiểm tra số lần gọi hàm mock chấm điểm
    assert mock_calculate_score.call_count == 2

    # Kiểm tra các tham số đã được gọi (không quan tâm thứ tự)
    task1 = sample_tasks_sent["task_s01"]
    result1 = sample_results_received_dict["task_s01"][0]
    task2 = sample_tasks_sent["task_s02"]
    result2 = sample_results_received_dict["task_s02"][0]

    # Dùng assert_any_call để kiểm tra từng lời gọi mong đợi
    mock_calculate_score.assert_any_call(task1.task_data, result1.result_data)
    mock_calculate_score.assert_any_call(task2.task_data, result2.result_data)
    # Kết hợp với call_count == 2 -> đảm bảo chỉ có 2 lời gọi này xảy ra

    # Check the returned scores dictionary (now contains lists)
    assert "task_s01" in validator_scores
    assert "task_s02" in validator_scores
    assert len(validator_scores["task_s01"]) == 1  # Only first valid result scored
    assert len(validator_scores["task_s02"]) == 1  # Only first valid result scored

    score_obj1 = validator_scores["task_s01"][0]
    score_obj2 = validator_scores["task_s02"][0]

    assert isinstance(score_obj1, ValidatorScore)
    assert score_obj1.task_id == "task_s01"
    assert score_obj1.miner_uid == task1.miner_uid
    assert score_obj1.validator_uid == validator_uid
    assert score_obj1.score == pytest.approx(expected_score1)

    assert isinstance(score_obj2, ValidatorScore)
    assert score_obj2.task_id == "task_s02"
    assert score_obj2.miner_uid == task2.miner_uid
    assert score_obj2.validator_uid == validator_uid
    assert score_obj2.score == pytest.approx(expected_score2)


def test_score_results_logic_no_results(
    mocker: MockerFixture,
    validator_uid: str,
    sample_tasks_sent: Dict[str, TaskAssignment],
):
    """Kiểm tra khi không có kết quả nào được nhận."""
    mock_calculate_score = mocker.patch(
        "sdk.consensus.scoring._calculate_score_from_result"
    )

    validator_scores = score_results_logic(
        validator_uid=validator_uid,
        results_received={},  # Empty Dict
        tasks_sent=sample_tasks_sent,
    )
    assert isinstance(validator_scores, dict)
    assert not validator_scores  # Dictionary rỗng
    mock_calculate_score.assert_not_called()


def test_score_results_logic_no_matching_task(
    mocker: MockerFixture,
    validator_uid: str,
    sample_results_received_dict: Dict[str, List[MinerResult]],
):
    """Kiểm tra khi kết quả nhận được không khớp với task nào đã gửi."""
    mock_calculate_score = mocker.patch(
        "sdk.consensus.scoring._calculate_score_from_result"
    )

    # Create a result dict with a key not in tasks_sent
    results_only_unmatched = {
        "task_s99": [
            MinerResult(
                task_id="task_s99",
                miner_uid="miner_S_C_hex",
                result_data={},
                timestamp_received=time.time(),
            )
        ]
    }

    validator_scores = score_results_logic(
        validator_uid=validator_uid,
        results_received=results_only_unmatched,
        tasks_sent={},  # No tasks sent
    )
    assert isinstance(validator_scores, dict)
    assert not validator_scores
    mock_calculate_score.assert_not_called()


def test_score_results_logic_duplicate_and_wrong_miner(
    mocker: MockerFixture,
    validator_uid: str,
    sample_results_received_dict: Dict[str, List[MinerResult]],
    sample_tasks_sent: Dict[str, TaskAssignment],
):
    """Kiểm tra chỉ chấm điểm kết quả hợp lệ đầu tiên, bỏ qua duplicate và sai miner."""
    mock_score = 0.8  # Điểm trả về giả lập
    mock_calculate_score = mocker.patch(
        "sdk.consensus.scoring._calculate_score_from_result", return_value=mock_score
    )

    # Input dict already contains duplicates and wrong miner from fixture
    validator_scores = score_results_logic(
        validator_uid=validator_uid,
        results_received=sample_results_received_dict,
        tasks_sent=sample_tasks_sent,
    )

    assert isinstance(validator_scores, dict)
    # Should have scored task_s01 (once) and task_s02 (once)
    assert len(validator_scores) == 2
    assert "task_s01" in validator_scores
    assert "task_s02" in validator_scores
    assert len(validator_scores["task_s01"]) == 1
    assert len(validator_scores["task_s02"]) == 1

    # Check mock was called only for the first valid result of each task
    assert mock_calculate_score.call_count == 2

    # Kiểm tra các tham số đã được gọi (không quan tâm thứ tự)
    task1 = sample_tasks_sent["task_s01"]
    result1 = sample_results_received_dict["task_s01"][0]
    task2 = sample_tasks_sent["task_s02"]
    result2 = sample_results_received_dict["task_s02"][0]

    # Dùng assert_any_call
    mock_calculate_score.assert_any_call(task1.task_data, result1.result_data)
    mock_calculate_score.assert_any_call(task2.task_data, result2.result_data)

    # Check results
    assert validator_scores["task_s01"][0].score == pytest.approx(mock_score)
    assert validator_scores["task_s02"][0].score == pytest.approx(mock_score)
