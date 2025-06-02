import pytest
import asyncio
from mt_aptos.monitoring.rate_limiter import RateLimiter

@pytest.fixture
def rate_limiter():
    return RateLimiter(max_requests=3, time_window=1)

@pytest.mark.asyncio
async def test_rate_limiter_acquire(rate_limiter):
    # Should allow 3 requests
    assert await rate_limiter.acquire()
    assert await rate_limiter.acquire()
    assert await rate_limiter.acquire()
    
    # Fourth request should be rejected
    assert not await rate_limiter.acquire()

@pytest.mark.asyncio
async def test_rate_limiter_reset(rate_limiter):
    # Use up all requests
    for _ in range(3):
        assert await rate_limiter.acquire()
    
    # Should be rejected
    assert not await rate_limiter.acquire()
    
    # Wait for window to reset
    await asyncio.sleep(1.1)
    
    # Should allow requests again
    assert await rate_limiter.acquire()

@pytest.mark.asyncio
async def test_rate_limiter_status(rate_limiter):
    # Check initial status
    status = rate_limiter.get_status()
    assert status["current_requests"] == 0
    assert status["max_requests"] == 3
    assert status["time_window"] == 1
    assert status["oldest_request"] is None
    
    # Make some requests
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    
    # Check updated status
    status = rate_limiter.get_status()
    assert status["current_requests"] == 2
    assert status["oldest_request"] is not None 