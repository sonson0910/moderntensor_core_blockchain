import time
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker pattern implementation for handling failures gracefully"""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.is_open = False

    async def execute(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from the function execution
            
        Raises:
            Exception: If circuit breaker is open or function execution fails
        """
        if self.is_open:
            if time.time() - self.last_failure_time > self.reset_timeout:
                logger.info("Circuit breaker resetting after timeout")
                self.is_open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                logger.warning(f"Circuit breaker opened after {self.failures} failures")
                self.is_open = True
            raise e

    def get_status(self) -> dict:
        """Get current circuit breaker status"""
        return {
            "is_open": self.is_open,
            "failures": self.failures,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout
        } 