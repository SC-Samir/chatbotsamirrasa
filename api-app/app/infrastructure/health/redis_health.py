"""
Redis health checker module.

This module provides health checking for Redis dependencies.
"""
import time
from typing import Any, Dict, Optional

from app.config import settings
from app.infrastructure.health.health_checker import (
    HealthCheckResult,
    HealthCheckerInterface,
    DependencyStatus,
)


class RedisHealthChecker(HealthCheckerInterface):
    """
    Health checker for Redis connections.
    
    Checks Redis connectivity and basic operations.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._name = "redis"
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> HealthCheckResult:
        """
        Perform Redis health check.
        
        Returns:
            HealthCheckResult with connection status and latency
        """
        start_time = time.time()
        
        if not self.redis_url:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="Redis URL not configured",
            )
        
        try:
            import redis.asyncio as redis
            
            # Try to connect and perform a simple operation
            redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Measure connection time
            connection_start = time.time()
            await redis_client.ping()
            connection_latency = (time.time() - connection_start) * 1000
            
            # Try a simple set/get operation
            test_key = f"health_check_{int(time.time())}"
            await redis_client.set(test_key, "1", ex=10)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            # Close connection
            await redis_client.close()
            
            total_latency = (time.time() - start_time) * 1000
            
            if value == "1":
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.CONNECTED,
                    latency_ms=total_latency,
                    details={
                        "url": self.redis_url,
                        "connection_latency_ms": round(connection_latency, 2),
                        "operations": ["ping", "set", "get", "delete"],
                    },
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.ERROR,
                    latency_ms=total_latency,
                    error="Redis read/write test failed",
                )
                
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="Redis client library not installed",
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_str = str(e)
            
            # Check for common connection errors
            if "ConnectionError" in str(type(e)) or "connection refused" in error_str.lower():
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.DISCONNECTED,
                    latency_ms=latency,
                    error=f"Connection refused: {error_str}",
                )
            elif "timeout" in error_str.lower():
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.TIMEOUT,
                    latency_ms=latency,
                    error=f"Connection timeout: {error_str}",
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.ERROR,
                    latency_ms=latency,
                    error=error_str,
                )
