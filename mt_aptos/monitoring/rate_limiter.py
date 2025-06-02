import time
import logging
from typing import Optional
from collections import deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter implementation using sliding window"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        
    async def acquire(self) -> bool:
        """
        Try to acquire a rate limit token
        
        Returns:
            bool: True if token acquired, False if rate limit exceeded
        """
        now = time.time()
        
        # Remove expired requests
        while self.requests and now - self.requests[0] > self.time_window:
            self.requests.popleft()
            
        if len(self.requests) >= self.max_requests:
            logger.warning(f"Rate limit exceeded: {len(self.requests)} requests in {self.time_window}s")
            return False
            
        self.requests.append(now)
        return True
        
    def get_status(self) -> dict:
        """Get current rate limiter status"""
        return {
            "current_requests": len(self.requests),
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "oldest_request": self.requests[0] if self.requests else None
        } 