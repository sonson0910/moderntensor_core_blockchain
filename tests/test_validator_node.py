import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sdk.consensus.node import ValidatorNode
from sdk.core.datatypes import ValidatorInfo, MinerInfo, TaskModel, MinerResult
from sdk.config.settings import settings

@pytest.fixture
def mock_validator_info():
    return ValidatorInfo(
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
    with patch('sdk.consensus.node.settings') as mock_settings:
        mock_settings.CONSENSUS_CYCLE_SLOT_LENGTH = 1
        mock_settings.HTTP_CLIENT_TIMEOUT = 30
        mock_settings.CONSENSUS_MAX_RETRIES = 3
        mock_settings.CONSENSUS_RETRY_DELAY_SECONDS = 1
        mock_settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
        mock_settings.CIRCUIT_BREAKER_RESET_TIMEOUT = 60
        mock_settings.RATE_LIMITER_MAX_REQUESTS = 100
        mock_settings.RATE_LIMITER_TIME_WINDOW = 60
        
        node = ValidatorNode(
            validator_info=mock_validator_info,
            aptos_client=mock_aptos_client,
            account=mock_account,
            contract_address="0x456"
        )
        return node

@pytest.mark.asyncio
async def test_circuit_breaker_integration(validator_node):
    # Test circuit breaker with network call
    async def mock_network_call():
        raise Exception("Network error")
    
    with pytest.raises(Exception):
        await validator_node.circuit_breaker.execute(mock_network_call)
    
    assert validator_node.circuit_breaker.failures == 1
    assert not validator_node.circuit_breaker.is_open

@pytest.mark.asyncio
async def test_rate_limiter_integration(validator_node):
    # Test rate limiter with task sending
    task = TaskModel(task_id="test_task", task_data={})
    
    # Should allow requests within limit
    for _ in range(3):
        assert await validator_node.rate_limiter.acquire()
    
    # Should reject when limit exceeded
    assert not await validator_node.rate_limiter.acquire()

@pytest.mark.asyncio
async def test_task_processing(validator_node):
    # Mock task and result
    task = TaskModel(task_id="test_task", task_data={"input": "test"})
    result = MinerResult(
        task_id="test_task",
        miner_uid="test_miner",
        result_data={"output": "test_result"}
    )
    
    # Mock task processing logic
    validator_node._process_task_logic = AsyncMock(return_value="processed")
    
    # Test task processing
    processed = await validator_node._process_task(task)
    assert processed == "processed"
    assert validator_node.metrics.task_processing_count > 0

@pytest.mark.asyncio
async def test_health_server_startup(validator_node):
    # Mock uvicorn server
    with patch('uvicorn.Server') as mock_server:
        mock_server.return_value.serve = AsyncMock()
        await validator_node.start_health_server()
        assert validator_node.health_server is not None

@pytest.mark.asyncio
async def test_metagraph_update(validator_node):
    # Mock metagraph data
    mock_miners = {
        "miner1": MinerInfo(uid="miner1", status=1),
        "miner2": MinerInfo(uid="miner2", status=1)
    }
    mock_validators = {
        "validator1": ValidatorInfo(uid="validator1", status=1)
    }
    
    # Mock load_metagraph_data
    validator_node.load_metagraph_data = AsyncMock()
    validator_node.miners_info = mock_miners
    validator_node.validators_info = mock_validators
    
    await validator_node._update_metagraph()
    assert validator_node.metrics.active_miners == 2
    assert validator_node.metrics.active_validators == 1

@pytest.mark.asyncio
async def test_task_sending_with_rate_limit(validator_node):
    # Mock miner
    miner = MinerInfo(
        uid="test_miner",
        api_endpoint="http://localhost:8001"
    )
    
    # Mock task creation
    validator_node._create_task_data = Mock(return_value={"test": "data"})
    
    # Mock HTTP client
    validator_node.http_client.post = AsyncMock(return_value=Mock(
        status_code=200,
        raise_for_status=Mock()
    ))
    
    # Test task sending
    await validator_node.send_task_and_track([miner])
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
    result = MinerResult(
        task_id=task_id,
        miner_uid=miner_uid,
        result_data={"output": "test_result"}
    )
    
    # Mock scoring logic
    validator_node._score_individual_result = Mock(return_value=0.8)
    
    # Test scoring
    await validator_node.add_miner_result(result)
    validator_node.score_miner_results()
    
    assert task_id in validator_node.validator_scores
    assert len(validator_node.validator_scores[task_id]) > 0 