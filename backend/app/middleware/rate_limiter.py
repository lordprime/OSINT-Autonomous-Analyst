"""
Rate Limiting Middleware
Protects API from abuse and DoS attacks
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time


class RateLimitConfig:
    """Rate limit configuration"""
    
    # Requests per minute per IP
    REQUESTS_PER_MINUTE = 60
    
    # Requests per hour per IP
    REQUESTS_PER_HOUR = 1000
    
    # Special limits for expensive operations
    COLLECTION_PER_HOUR = 100
    LLM_CALLS_PER_HOUR = 500
    
    # Burst allowance (short-term spike)
    BURST_SIZE = 10


class RateLimiter:
    """
    In-memory rate limiter with sliding window
    
    Production: Replace with Redis for distributed rate limiting
    """
    
    def __init__(self):
        # {ip: [(timestamp, endpoint), ...]}
        self.requests: Dict[str, list[Tuple[float, str]]] = {}
        self.blocked_ips: Dict[str, float] = {}  # {ip: unblock_time}
    
    def is_allowed(
        self,
        client_ip: str,
        endpoint: str,
        now: float = None
    ) -> Tuple[bool, str]:
        """
        Check if request is allowed
        
        Returns:
            (allowed, reason) tuple
        """
        
        now = now or time.time()
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            unblock_time = self.blocked_ips[client_ip]
            if now < unblock_time:
                remaining = int(unblock_time - now)
                return False, f"IP blocked for {remaining}s due to rate limit violation"
            else:
                # Unblock
                del self.blocked_ips[client_ip]
        
        # Clean old requests (older than 1 hour)
        self._cleanup(client_ip, now)
        
        # Get request history
        history = self.requests.get(client_ip, [])
        
        # Check minute rate
        minute_ago = now - 60
        recent_requests = [r for r in history if r[0] > minute_ago]
        if len(recent_requests) >= RateLimitConfig.REQUESTS_PER_MINUTE:
            self._block_ip(client_ip, now, duration=60)
            return False, f"Rate limit: {RateLimitConfig.REQUESTS_PER_MINUTE} req/min exceeded"
        
        # Check hour rate
        hour_ago = now - 3600
        hourly_requests = [r for r in history if r[0] > hour_ago]
        if len(hourly_requests) >= RateLimitConfig.REQUESTS_PER_HOUR:
            self._block_ip(client_ip, now, duration=300)  # Block for 5 min
            return False, f"Rate limit: {RateLimitConfig.REQUESTS_PER_HOUR} req/hour exceeded"
        
        # Check endpoint-specific limits
        if "/collection/" in endpoint:
            collection_count = len([r for r in hourly_requests if "/collection/" in r[1]])
            if collection_count >= RateLimitConfig.COLLECTION_PER_HOUR:
                return False, f"Collection limit: {RateLimitConfig.COLLECTION_PER_HOUR}/hour exceeded"
        
        if "/reasoning/" in endpoint:
            llm_count = len([r for r in hourly_requests if "/reasoning/" in r[1]])
            if llm_count >= RateLimitConfig.LLM_CALLS_PER_HOUR:
                return False, f"LLM limit: {RateLimitConfig.LLM_CALLS_PER_HOUR}/hour exceeded"
        
        # Allow request
        return True, ""
    
    def record_request(self, client_ip: str, endpoint: str, now: float = None):
        """Record successful request"""
        
        now = now or time.time()
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        self.requests[client_ip].append((now, endpoint))
    
    def _cleanup(self, client_ip: str, now: float):
        """Remove old requests from history"""
        
        if client_ip not in self.requests:
            return
        
        hour_ago = now - 3600
        self.requests[client_ip] = [
            r for r in self.requests[client_ip] if r[0] > hour_ago
        ]
    
    def _block_ip(self, client_ip: str, now: float, duration: int):
        """Temporarily block IP"""
        
        self.blocked_ips[client_ip] = now + duration
    
    def get_stats(self, client_ip: str) -> Dict:
        """Get rate limit stats for IP"""
        
        now = time.time()
        history = self.requests.get(client_ip, [])
        
        minute_ago = now - 60
        hour_ago = now - 3600
        
        recent = len([r for r in history if r[0] > minute_ago])
        hourly = len([r for r in history if r[0] > hour_ago])
        
        return {
            "requests_last_minute": recent,
            "requests_last_hour": hourly,
            "minute_limit": RateLimitConfig.REQUESTS_PER_MINUTE,
            "hour_limit": RateLimitConfig.REQUESTS_PER_HOUR,
            "minute_remaining": max(0, RateLimitConfig.REQUESTS_PER_MINUTE - recent),
            "hour_remaining": max(0, RateLimitConfig.REQUESTS_PER_HOUR - hourly)
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/status"]:
            return await call_next(request)
        
        # Check rate limit
        allowed, reason = rate_limiter.is_allowed(client_ip, request.url.path)
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": reason,
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Reset": str(int(time.time()) + 60)
                }
            )
        
        # Record request
        rate_limiter.record_request(client_ip, request.url.path)
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        stats = rate_limiter.get_stats(client_ip)
        response.headers["X-RateLimit-Limit"] = str(RateLimitConfig.REQUESTS_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(stats["minute_remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response


# Helper function to add to FastAPI app
def add_rate_limiting(app):
    """Add rate limiting middleware to FastAPI app"""
    
    app.add_middleware(RateLimitMiddleware)
    print("✅ Rate limiting enabled")
