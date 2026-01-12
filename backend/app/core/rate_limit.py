"""
Rate Limiting Manager - Token bucket algorithm with Redis backend.
Prevents API rate limit violations and IP bans.
"""

import time
import asyncio
from typing import Optional
import logging

from app.core.database import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Rate Limiter
# ============================================

class RateLimiter:
    """
    Token bucket rate limiter with Redis backend.
    
    Prevents:
    - API rate limit violations (429 errors)
    - IP bans from aggressive scraping
    - Detection of automated tools
    """
    
    def __init__(
        self,
        source: str,
        requests_per_minute: int,
        burst: int = 10
    ):
        """
        Args:
            source: Source identifier (twitter, reddit, etc.)
            requests_per_minute: Sustained rate limit
            burst: Maximum burst requests
        """
        self.source = source
        self.rpm = requests_per_minute
        self.burst = burst
        self.redis_key = f"rate_limit:{source}"
        
        # Calculate token refill rate
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.
        Blocks until tokens are available.
        
        Args:
            tokens: Number of tokens to acquire
        
        Returns:
            True when tokens acquired
        """
        while True:
            allowed = await self._try_acquire(tokens)
            if allowed:
                return True
            
            # Wait before retry
            wait_time = self._calculate_wait_time(tokens)
            logger.debug(f"Rate limit: {self.source} - Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
    
    async def _try_acquire(self, tokens: int) -> bool:
        """
        Try to acquire tokens without blocking.
        
        Returns:
            True if tokens acquired, False if rate limited
        """
        now = time.time()
        
        # Get current bucket state from Redis
        bucket_data = redis_client.get(self.redis_key)
        
        if bucket_data:
            # Parse existing bucket
            available_tokens, last_refill = map(float, bucket_data.split(":"))
        else:
            # Initialize new bucket
            available_tokens = float(self.burst)
            last_refill = now
        
        # Refill tokens based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        available_tokens = min(self.burst, available_tokens + tokens_to_add)
        
        # Check if we have enough tokens
        if available_tokens >= tokens:
            # Consume tokens
            available_tokens -= tokens
            
            # Update Redis
            redis_client.setex(
                self.redis_key,
                3600,  # 1 hour TTL
                f"{available_tokens}:{now}"
            )
            
            return True
        else:
            # Not enough tokens
            return False
    
    def _calculate_wait_time(self, tokens: int) -> float:
        """Calculate how long to wait for tokens"""
        # Wait for tokens to refill
        return tokens / self.refill_rate

# ============================================
# Rate Limit Manager
# ============================================

class RateLimitManager:
    """
    Manages rate limiters for all collection sources.
    """
    
    def __init__(self):
        self.limiters = {}
        self._initialize_limiters()
    
    def _initialize_limiters(self):
        """Initialize rate limiters for each source"""
        
        # Twitter/X - Very restrictive
        self.limiters["twitter"] = RateLimiter(
            source="twitter",
            requests_per_minute=settings.RATE_LIMIT_TWITTER,
            burst=5
        )
        
        # Reddit - More permissive
        self.limiters["reddit"] = RateLimiter(
            source="reddit",
            requests_per_minute=settings.RATE_LIMIT_REDDIT,
            burst=20
        )
        
        # Shodan - Extremely restrictive
        self.limiters["shodan"] = RateLimiter(
            source="shodan",
            requests_per_minute=settings.RATE_LIMIT_SHODAN,
            burst=1
        )
        
        # Google (for dorking) - Moderate
        self.limiters["google"] = RateLimiter(
            source="google",
            requests_per_minute=10,
            burst=5
        )
        
        logger.info(f"Initialized {len(self.limiters)} rate limiters")
    
    async def acquire(self, source: str, tokens: int = 1) -> bool:
        """
        Acquire rate limit tokens for a source.
        
        Args:
            source: Source identifier
            tokens: Number of tokens to acquire
        
        Returns:
            True when tokens acquired
        """
        if source not in self.limiters:
            logger.warning(f"No rate limiter for source: {source}")
            return True  # Allow if no limiter configured
        
        return await self.limiters[source].acquire(tokens)
    
    def get_status(self, source: str) -> dict:
        """Get current rate limit status for a source"""
        if source not in self.limiters:
            return {"error": "Unknown source"}
        
        limiter = self.limiters[source]
        bucket_data = redis_client.get(limiter.redis_key)
        
        if bucket_data:
            available_tokens, last_refill = map(float, bucket_data.split(":"))
            return {
                "source": source,
                "available_tokens": available_tokens,
                "max_tokens": limiter.burst,
                "refill_rate": limiter.refill_rate,
                "last_refill": last_refill
            }
        else:
            return {
                "source": source,
                "available_tokens": limiter.burst,
                "max_tokens": limiter.burst,
                "refill_rate": limiter.refill_rate
            }

# ============================================
# Global Rate Limit Manager
# ============================================

rate_limit_manager = RateLimitManager()
