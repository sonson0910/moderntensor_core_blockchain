import pytest
import asyncio
from sdk.monitoring.circuit_breaker import CircuitBreaker

@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(failure_threshold=3, reset_timeout=1)

@pytest.mark.asyncio
async def test_circuit_breaker_success(circuit_breaker):
    async def success_func():
        return "success"
    
    result = await circuit_breaker.execute(success_func)
    assert result == "success"
    assert not circuit_breaker.is_open
    assert circuit_breaker.failures == 0

@pytest.mark.asyncio
async def test_circuit_breaker_failure(circuit_breaker):
    async def fail_func():
        raise Exception("test error")
    
    with pytest.raises(Exception):
        await circuit_breaker.execute(fail_func)
    
    assert circuit_breaker.failures == 1
    assert not circuit_breaker.is_open

@pytest.mark.asyncio
async def test_circuit_breaker_opens(circuit_breaker):
    async def fail_func():
        raise Exception("test error")
    
    # Fail multiple times
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.execute(fail_func)
    
    assert circuit_breaker.is_open
    assert circuit_breaker.failures == 3

@pytest.mark.asyncio
async def test_circuit_breaker_resets(circuit_breaker):
    async def fail_func():
        raise Exception("test error")
    
    # Open the circuit
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.execute(fail_func)
    
    assert circuit_breaker.is_open
    
    # Wait for reset timeout
    await asyncio.sleep(1.1)
    
    # Should be closed again
    assert not circuit_breaker.is_open
    assert circuit_breaker.failures == 0 