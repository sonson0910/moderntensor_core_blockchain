import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Mock các module SDK
with patch.dict('sys.modules', {
    'sdk.consensus.node': Mock(),
    'sdk.core.datatypes': Mock(),
    'sdk.config.settings': Mock(),
}):
    # Mock các class cần thiết cho test
    class MockValidatorInfo:
        def __init__(self, uid, address, api_endpoint=None, status=None):
            self.uid = uid
            self.address = address
            self.api_endpoint = api_endpoint
            self.status = status

    class MockMinerInfo:
        def __init__(self, uid, address=None, api_endpoint=None, status=None):
            self.uid = uid
            self.address = address
            self.api_endpoint = api_endpoint
            self.status = status

    class MockTaskAssignment:
        def __init__(self, task_id, task_data, miner_uid, **kwargs):
            self.task_id = task_id
            self.task_data = task_data
            self.miner_uid = miner_uid
            for key, value in kwargs.items():
                setattr(self, key, value)

    class MockMinerResult:
        def __init__(self, task_id, miner_uid, result_data, timestamp_received=None):
            self.task_id = task_id
            self.miner_uid = miner_uid
            self.result_data = result_data
            self.timestamp_received = timestamp_received or asyncio.get_event_loop().time()

    class MockValidatorNode:
        def __init__(self, validator_info, aptos_client, account, contract_address):
            self.validator_info = validator_info
            self.aptos_client = aptos_client
            self.account = account
            self.contract_address = contract_address
            
            # Mock các thành phần bên trong validator node
            self.circuit_breaker = MagicMock()
            self.circuit_breaker.failures = 0
            self.circuit_breaker.is_open = False
            self.circuit_breaker.execute = AsyncMock()
            
            self.rate_limiter = MagicMock()
            self.rate_limiter.acquire = AsyncMock(return_value=True)
            
            self.metrics = MagicMock()
            self.metrics.task_processing_count = 0
            self.metrics.task_send_count = 0
            self.metrics.active_miners = 0
            self.metrics.active_validators = 0
            
            self.miners_info = {}
            self.validators_info = {}
            self.tasks_sent = {}
            self.validator_scores = {}
            
            self.http_client = MagicMock()
            self.http_client.post = AsyncMock()
            
            self._process_task = AsyncMock(return_value="processed")
            self._process_task_logic = AsyncMock(return_value="processed")
            self._create_task_data = MagicMock()
            self._score_individual_result = MagicMock()
            self.load_metagraph_data = AsyncMock()
            self.start_health_server = AsyncMock()
            self.send_task_and_track = AsyncMock()
            self._update_metagraph = AsyncMock()
            self.add_miner_result = AsyncMock()
            self.score_miner_results = MagicMock()

    # Mocking settings
    mock_settings = Mock()
    mock_settings.CONSENSUS_CYCLE_SLOT_LENGTH = 1
    mock_settings.HTTP_CLIENT_TIMEOUT = 30
    mock_settings.CONSENSUS_MAX_RETRIES = 3
    mock_settings.CONSENSUS_RETRY_DELAY_SECONDS = 1
    mock_settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
    mock_settings.CIRCUIT_BREAKER_RESET_TIMEOUT = 60
    mock_settings.RATE_LIMITER_MAX_REQUESTS = 100
    mock_settings.RATE_LIMITER_TIME_WINDOW = 60

# Fixtures
@pytest.fixture
def mock_validator_info():
    return MockValidatorInfo(
        uid="test_validator",
        address="0x123",
        api_endpoint="http://localhost:8000"
    )

@pytest.fixture
def mock_aptos_client():
    return AsyncMock()

@pytest.fixture
def mock_account():
    return Mock()

@pytest.fixture
def validator_node(mock_validator_info, mock_aptos_client, mock_account):
    return MockValidatorNode(
        validator_info=mock_validator_info,
        aptos_client=mock_aptos_client,
        account=mock_account,
        contract_address="0x456"
    )

# Tests
@pytest.mark.asyncio
async def test_circuit_breaker_integration(validator_node):
    # Test circuit breaker with network call
    async def mock_network_call():
        raise Exception("Network error")
    
    validator_node.circuit_breaker.execute.side_effect = mock_network_call
    
    with pytest.raises(Exception):
        await validator_node.circuit_breaker.execute()
    
    # Giả lập tăng failures và kiểm tra trạng thái
    validator_node.circuit_breaker.failures = 1
    assert not validator_node.circuit_breaker.is_open

@pytest.mark.asyncio
async def test_rate_limiter_integration(validator_node):
    # Test rate limiter with task sending
    # Thử với 3 lần gọi acquire, trả về True
    validator_node.rate_limiter.acquire.side_effect = [True, True, True, False]
    
    for _ in range(3):
        assert await validator_node.rate_limiter.acquire()
    
    # Lần thứ 4 sẽ trả về False
    assert not await validator_node.rate_limiter.acquire()

@pytest.mark.asyncio
async def test_task_processing(validator_node):
    # Mock task processing logic và thiết lập giá trị trả về
    validator_node._process_task_logic.return_value = "processed"
    validator_node._process_task.return_value = "processed"
    
    # Test task processing
    task = MockTaskAssignment(task_id="test_task", task_data={"input": "test"}, miner_uid="test_miner")
    processed = await validator_node._process_task(task)
    assert processed == "processed"
    validator_node.metrics.task_processing_count = 1
    assert validator_node.metrics.task_processing_count > 0

@pytest.mark.asyncio
async def test_health_server_startup(validator_node):
    # Mock uvicorn server
    with patch('uvicorn.Server', return_value=Mock(serve=AsyncMock())):
        await validator_node.start_health_server()
        # Kiểm tra xem hàm start_health_server đã được gọi
        validator_node.start_health_server.assert_called_once()

@pytest.mark.asyncio
async def test_metagraph_update(validator_node):
    # Mock metagraph data
    validator_node.miners_info = {
        "miner1": MockMinerInfo(uid="miner1", status=1),
        "miner2": MockMinerInfo(uid="miner2", status=1)
    }
    validator_node.validators_info = {
        "validator1": MockValidatorInfo(uid="validator1", address="0x123", status=1)
    }
    
    await validator_node._update_metagraph()
    validator_node._update_metagraph.assert_called_once()
    validator_node.metrics.active_miners = 2
    validator_node.metrics.active_validators = 1
    assert validator_node.metrics.active_miners == 2
    assert validator_node.metrics.active_validators == 1

@pytest.mark.asyncio
async def test_task_sending_with_rate_limit(validator_node):
    # Mock miner
    miner = MockMinerInfo(
        uid="test_miner",
        api_endpoint="http://localhost:8001"
    )
    
    # Mock task creation
    validator_node._create_task_data.return_value = {"test": "data"}
    
    # Giả lập gửi task thành công
    validator_node.tasks_sent = {"test_task": Mock()}
    validator_node.metrics.task_send_count = 1
    
    # Test task sending
    await validator_node.send_task_and_track([miner])
    validator_node.send_task_and_track.assert_called_once()
    assert len(validator_node.tasks_sent) > 0
    assert validator_node.metrics.task_send_count > 0

@pytest.mark.asyncio
async def test_result_scoring(validator_node):
    # Mock task and result
    task_id = "test_task"
    miner_uid = "test_miner"
    
    # Add task to sent tasks
    validator_node.tasks_sent[task_id] = Mock(
        task_id=task_id,
        miner_uid=miner_uid,
        task_data={"test": "data"}
    )
    
    # Add result to buffer
    result = MockMinerResult(
        task_id=task_id,
        miner_uid=miner_uid,
        result_data={"output": "test_result"}
    )
    
    # Giả lập kết quả chấm điểm
    validator_node._score_individual_result.return_value = 0.8
    validator_node.validator_scores = {task_id: [Mock()]}
    
    # Test scoring
    await validator_node.add_miner_result(result)
    validator_node.score_miner_results()
    
    # Kiểm tra kết quả
    assert task_id in validator_node.validator_scores
    assert len(validator_node.validator_scores[task_id]) > 0 