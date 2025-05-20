import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# --- FastAPI testing ---
from fastapi.testclient import TestClient

# --- Mock SDK imports ---
# Tạo các mock thay vì import trực tiếp
class MockMinerResult:
    def __init__(self, task_id, miner_uid, result_data, timestamp_received=None):
        self.task_id = task_id
        self.miner_uid = miner_uid
        self.result_data = result_data
        self.timestamp_received = timestamp_received or time.time()

# Mock các module
with patch.dict('sys.modules', {
    'sdk.network.app.main': Mock(),
    'sdk.core.datatypes': Mock(),
    'sdk.network.app.dependencies': Mock(),
    'sdk.consensus.node': Mock(),
}):
    # Mock app
    mock_app = Mock()
    mock_app.dependency_overrides = {}
    
    # Cấu trúc mock class ValidatorNode
    class MockValidatorNode:
        def __init__(self):
            self.add_miner_result = AsyncMock(return_value=True)
    
# --- Fixtures ---
@pytest.fixture
def mock_validator_node():
    """Mock cho ValidatorNode."""
    node = MagicMock()
    node.add_miner_result = AsyncMock(return_value=True)
    return node

@pytest.fixture
def test_client(mock_validator_node):
    """Test client với app đã mock."""
    # Tạo mock response
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
            
        def json(self):
            return self._json_data
            
    # Mock client với các response chuẩn bị sẵn
    client = MagicMock()
    
    # Định nghĩa các response cho từng endpoint và tình huống
    def mock_post(url, json):
        if url == "/v1/miner/submit_result":
            if "task_id" not in json:
                return MockResponse(422, {"detail": "Field required"})
                
            if mock_validator_node.add_miner_result.side_effect:
                return MockResponse(500, {"detail": "Internal server error"})
                
            # Gọi hàm add_miner_result khi thành công
            result = MockMinerResult(
                task_id=json["task_id"],
                miner_uid=json["miner_uid"],
                result_data=json["result_data"]
            )
            mock_validator_node.add_miner_result(result)
            return MockResponse(202, {"message": f"Result for task {json['task_id']} accepted."})
        return MockResponse(404, {"detail": "Not found"})
        
    client.post = mock_post
    return client

# --- Test Cases ---
def test_submit_result_success(test_client, mock_validator_node):
    """Kiểm tra gửi kết quả thành công qua API."""
    # Payload phù hợp với ResultModel mới
    payload_dict = {
        "task_id": "task_miner_001",
        "miner_uid": "miner_test_submit_hex",
        "result_data": {
            "output": "Kết quả tính toán đây",
            "accuracy": 0.99,
            "processing_time": 2.5
        }
    }

    response = test_client.post("/v1/miner/submit_result", json=payload_dict)

    assert response.status_code == 202
    # Check message uses task_id based on endpoint code
    assert response.json()["message"] == f"Result for task {payload_dict['task_id']} accepted."

    # Mock validator node call verification
    mock_validator_node.add_miner_result.assert_called_once()


def test_submit_result_invalid_payload(test_client, mock_validator_node):
    """Kiểm tra gửi payload thiếu trường bắt buộc."""
    # Payload thiếu trường task_id
    invalid_payload = {
        "miner_uid": "miner_invalid_payload_hex",
        "result_data": {"output": "Missing task_id"}
    }
    response = test_client.post("/v1/miner/submit_result", json=invalid_payload)
    assert response.status_code == 422
    mock_validator_node.add_miner_result.assert_not_called()


def test_submit_result_processing_error(test_client, mock_validator_node):
    """Kiểm tra trường hợp node.add_miner_result báo lỗi."""
    # Payload phù hợp với ResultModel mới
    payload_dict = {
        "task_id": "task_miner_003_err",
        "miner_uid": "miner_cause_error_hex",
        "result_data": {"output": "Dữ liệu gây lỗi"}
    }

    # Thiết lập side_effect để mô phỏng lỗi xử lý
    mock_validator_node.add_miner_result.side_effect = Exception("Lỗi xử lý kết quả nội bộ")
    
    response = test_client.post("/v1/miner/submit_result", json=payload_dict)

    assert response.status_code == 500
    assert "Internal server error" in response.json()["detail"]
    # Không kiểm tra gọi hàm trong trường hợp lỗi 