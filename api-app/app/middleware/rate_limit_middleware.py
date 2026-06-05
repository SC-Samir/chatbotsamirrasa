"""
Rate limiting middleware.

This middleware implements rate limiting for API endpoints using
token bucket or fixed window algorithms.
"""
import time
from collections import defaultdict
from typing import Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
import asyncio

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.core.logging import StructuredLogger

logger = StructuredLogger("rate_limit_middleware")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 100
    window_seconds: int = 60
    burst_requests: Optional[int] = None
    burst_seconds: Optional[int] = None
    
    def __post_init__(self):
        if self.burst_requests is None:
            self.burst_requests = self.max_requests
        if self.burst_seconds is None:
            self.burst_seconds = self.window_seconds


class RateLimitStore:
    """
    Store for tracking request counts.
    
    Uses in-memory storage by default, can be extended to use Redis
    for distributed rate limiting.
    """
    
    def __init__(self):
        # Format: {identifier: [(timestamp, count), ...]}
        self.requests: dict = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def add_request(self, identifier: str, current_time: float) -> Tuple[int, int]:
        """
        Add a request and return current count and remaining.
        
        Args:
            identifier: Unique identifier (IP, user, API key)
            current_time: Current timestamp
            
        Returns:
            Tuple of (current_count, remaining)
        """
        async with self.lock:
            # Clean up old entries
            window_start = current_time - 60  # Clean up entries older than 1 minute
            self.requests[identifier] = [
                (ts, count) for ts, count in self.requests[identifier]
                if ts > window_start
            ]
            
            # Get current count in window
            current_window_start = current_time - 1  # Last second
            current_count = sum(
                count for ts, count in self.requests[identifier]
                if ts >= current_window_start
            )
            
            # Add this request
            self.requests[identifier].append((current_time, 1))
            
            return current_count + 1, current_count
    
    async def get_count(self, identifier: str, current_time: float, window: int) -> int:
        """
        Get request count for identifier in the specified window.
        
        Args:
            identifier: Unique identifier
            current_time: Current timestamp
            window: Window in seconds
            
        Returns:
            Request count in window
        """
        async with self.lock:
            window_start = current_time - window
            return sum(
                count for ts, count in self.requests[identifier]
                if ts >= window_start
            )
    
    async def cleanup(self, max_age: int = 300) -> None:
        """
        Clean up old entries.
        
        Args:
            max_age: Maximum age in seconds
        """
        async with self.lock:
            current_time = time.time()
            for identifier in list(self.requests.keys()):
                self.requests[identifier] = [
                    (ts, count) for ts, count in self.requests[identifier]
                    if ts > current_time - max_age
                ]
                if not self.requests[identifier]:
                    del self.requests[identifier]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Implements token bucket algorithm with sliding window for rate limiting.
    Can limit by IP address, user, API key, or any combination.
    """
    
    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        limit_by: str = "ip",
        exclude_paths: Optional[list] = None,
        store: Optional[RateLimitStore] = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.config = config or RateLimitConfig(
            max_requests=100,
            window_seconds=60,
        )
        self.limit_by = limit_by  # Can be: "ip", "user", "api_key", "combined"
        self.exclude_paths = exclude_paths or [
            "/health",
            "/health/",
            "/health/ready",
            "/health/live",
            "/health/metrics",
            "/health/info",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/",
            "/static",
        ]
        self.store = store or RateLimitStore()
        self.enabled = enabled
    
    def _get_identifier(self, request: Request) -> str:
        """
        Get the identifier for rate limiting.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Unique identifier string
        """
        if self.limit_by == "ip":
            # Use client IP
            if request.client:
                return f"ip:{request.client.host}"
            # Check forwarded headers
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return f"ip:{forwarded.split(',')[0].strip()}"
            return "ip:unknown"
        
        elif self.limit_by == "user":
            # Use authenticated user
            if hasattr(request.state, 'user_info') and request.state.user_info:
                user_id = request.state.user_info.get('user_id', 'anonymous')
                return f"user:{user_id}"
            return "user:anonymous"
        
        elif self.limit_by == "api_key":
            # Use API key
            api_key = request.headers.get("X-API-Key")
            if api_key:
                return f"api_key:{api_key[:20]}..."
            return "api_key:anonymous"
        
        elif self.limit_by == "combined":
            # Combine IP and user
            ip_part = "unknown"
            if request.client:
                ip_part = request.client.host
            user_part = "anonymous"
            if hasattr(request.state, 'user_info') and request.state.user_info:
                user_part = request.state.user_info.get('user_id', 'anonymous')
            return f"combined:{ip_part}:{user_part}"
        
        return "default"
    
    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting."""
        for exclude_path in self.exclude_paths:
            if path == exclude_path or path.startswith(exclude_path + "/"):
                return True
            if exclude_path.endswith("/") and path.startswith(exclude_path):
                return True
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Dispatch request with rate limiting."""
        if not self.enabled:
            return await call_next(request)
        
        path = request.url.path
        
        # Skip rate limiting for excluded paths
        if self._should_exclude(path):
            return await call_next(request)
        
        # Get identifier
        identifier = self._get_identifier(request)
        current_time = time.time()
        
        # Check rate limit
        request_count = await self.store.get_count(
            identifier,
            current_time,
            self.config.window_seconds,
        )
        
        if request_count >= self.config.max_requests:
            # Rate limit exceeded
            retry_after = self.config.window_seconds - (current_time % self.config.window_seconds)
            
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                path=path,
                method=request.method,
                count=request_count,
                limit=self.config.max_requests,
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(int(retry_after + 1)),
                    "X-RateLimit-Limit": str(self.config.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + retry_after)),
                },
            )
        
        # Add this request
        current_count, _ = await self.store.add_request(identifier, current_time)
        remaining = max(0, self.config.max_requests - current_count)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if hasattr(response, 'headers'):
            response.headers["X-RateLimit-Limit"] = str(self.config.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(current_time + self.config.window_seconds))
        
        return response


class RedisRateLimitStore(RateLimitStore):
    """
    Redis-based store for distributed rate limiting.
    
    This store uses Redis for tracking request counts across multiple instances.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        super().__init__()
        self.redis_url = redis_url or settings.redis_url
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None and self.redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except ImportError:
                logger.warning("Redis client not installed, falling back to in-memory store")
        return self._redis
    
    async def add_request(self, identifier: str, current_time: float) -> Tuple[int, int]:
        """Add request using Redis."""
        redis_client = await self._get_redis()
        if redis_client is None:
            return await super().add_request(identifier, current_time)
        
        try:
            # Use Redis INCR with expiration
            key = f"rate_limit:{identifier}:{int(current_time)}"
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, 60)  # Expire after 60 seconds
            
            return count, count - 1
        except Exception as e:
            logger.warning(f"Redis rate limit error: {e}")
            return await super().add_request(identifier, current_time)
    
    async def get_count(self, identifier: str, current_time: float, window: int) -> int:
        """Get count using Redis."""
        redis_client = await self._get_redis()
        if redis_client is None:
            return await super().get_count(identifier, current_time, window)
        
        try:
            # Sum counts across all seconds in the window
            total = 0
            current_second = int(current_time)
            for i in range(window):
                key = f"rate_limit:{identifier}:{current_second - i}"
                count = await redis_client.get(key)
                if count:
                    total += int(count)
            return total
        except Exception as e:
            logger.warning(f"Redis rate limit count error: {e}")
            return await super().get_count(identifier, current_time, window)


def create_rate_limit_middleware(
    max_requests: int = 100,
    window_seconds: int = 60,
    limit_by: str = "ip",
    use_redis: bool = False,
) -> RateLimitMiddleware:
    """
    Factory function to create rate limiting middleware.
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Window size in seconds
        limit_by: What to limit by ("ip", "user", "api_key", "combined")
        use_redis: Whether to use Redis for distributed rate limiting
        
    Returns:
        RateLimitMiddleware instance
    """
    config = RateLimitConfig(
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    
    if use_redis:
        store = RedisRateLimitStore()
    else:
        store = RateLimitStore()
    
    return RateLimitMiddleware(
        app=None,
        config=config,
        limit_by=limit_by,
        store=store,
    )
