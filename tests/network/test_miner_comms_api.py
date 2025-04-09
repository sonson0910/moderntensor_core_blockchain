# tests/network/test_miner_comms_api.py
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, ANY

# --- FastAPI testing ---
from fastapi.testclient import TestClient
# --- REMOVE Local ResultModel Definition ---

# --- SDK imports ---
from sdk.network.app.main import app
from sdk.core.datatypes import MinerResult # Internal dataclass
from sdk.network.app.dependencies import get_validator_node
from sdk.consensus.node import ValidatorNode

# --- Fixtures (Keep as is) ---
@pytest.fixture
def mock_validator_node() -> MagicMock:
    mock_node = MagicMock(spec=ValidatorNode)
    mock_node.add_miner_result = AsyncMock(return_value=True) # Return True for success case
    return mock_node

@pytest.fixture
def test_client(mock_validator_node: MagicMock):
    app.dependency_overrides[get_validator_node] = lambda: mock_validator_node
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

# --- Test Cases ---
def test_submit_result_success(test_client: TestClient, mock_validator_node: MagicMock):
    """Kiểm tra gửi kết quả thành công qua API."""
    # ===>>> CORRECT PAYLOAD TO MATCH server.py ResultModel <<<===
    payload_dict = {
        "result_id": "task_miner_001", # Use result_id (as task identifier for endpoint)
        "description": '{"output": "Kết quả tính toán đây", "accuracy": 0.99}', # Put result data in description
        "processing_time": 2.5,
        "miner_id": "miner_test_submit_hex" # Use miner_id
    }
    # ===>>> END CORRECTION <<<===

    response = test_client.post("/v1/miner/submit_result", json=payload_dict)

    assert response.status_code == 202
    # Check message uses result_id based on endpoint code
    assert response.json()["message"] == f"Result for task {payload_dict['result_id']} accepted."

    mock_validator_node.add_miner_result.assert_awaited_once()
    call_args, _ = mock_validator_node.add_miner_result.call_args
    received: MinerResult = call_args[0]

    # Check internal MinerResult based on endpoint's mapping logic
    assert isinstance(received, MinerResult)
    assert received.task_id == payload_dict["result_id"] # Endpoint uses result_id for task_id
    assert received.miner_uid == payload_dict["miner_id"] # Endpoint uses miner_id for miner_uid
    # Check how endpoint constructs result_data
    assert received.result_data["description"] == payload_dict["description"]
    assert received.result_data["processing_time"] == payload_dict["processing_time"]
    assert time.time() - received.timestamp_received < 5

def test_submit_result_invalid_payload(test_client: TestClient, mock_validator_node: MagicMock):
    """Kiểm tra gửi payload thiếu trường bắt buộc."""
    # Payload missing required 'result_id' from ResultModel
    invalid_payload = {
        "description": "Missing fields",
        "processing_time": 1.0,
        "miner_id": "miner_invalid_payload_hex"
    }
    response = test_client.post("/v1/miner/submit_result", json=invalid_payload)
    assert response.status_code == 422
    mock_validator_node.add_miner_result.assert_not_awaited()

def test_submit_result_processing_error(test_client: TestClient, mock_validator_node: MagicMock):
    """Kiểm tra trường hợp node.add_miner_result báo lỗi."""
    # ===>>> CORRECT PAYLOAD TO MATCH server.py ResultModel <<<===
    payload_dict = {
        "result_id": "task_miner_003_err", # Use result_id
        "description": '{"output": "Dữ liệu gây lỗi"}', # Put result data in description
        "processing_time": 0.8,
        "miner_id": "miner_cause_error_hex" # Use miner_id
    }
    # ===>>> END CORRECTION <<<===

    mock_validator_node.add_miner_result.side_effect = Exception("Lỗi xử lý kết quả nội bộ")
    # --- Ensure endpoint's try...except covers the await call ---
    # If the endpoint code fix wasn't applied, this might still fail with raw Exception
    response = test_client.post("/v1/miner/submit_result", json=payload_dict)

    assert response.status_code == 500
    assert "Internal server error" in response.json()["detail"]
    mock_validator_node.add_miner_result.assert_awaited_once()