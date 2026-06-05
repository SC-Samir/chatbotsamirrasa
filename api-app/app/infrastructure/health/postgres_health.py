"""
PostgreSQL health checker module.

This module provides health checking for PostgreSQL database connections.
"""
import time
from typing import Any, Optional

from app.config import settings
from app.infrastructure.health.health_checker import (
    HealthCheckResult,
    HealthCheckerInterface,
    DependencyStatus,
)


class PostgresHealthChecker(HealthCheckerInterface):
    """
    Health checker for PostgreSQL database connections.
    
    Checks database connectivity and basic query execution.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url or settings.memory_postgres_dsn
        self._name = "postgres"
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> HealthCheckResult:
        """
        Perform PostgreSQL health check.
        
        Returns:
            HealthCheckResult with connection status and latency
        """
        start_time = time.time()
        
        if not self.database_url:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="PostgreSQL URL not configured",
            )
        
        try:
            import psycopg
            from psycopg import sql
            
            # Connect to the database
            connection_start = time.time()
            conn = psycopg.connect(self.database_url)
            connection_latency = (time.time() - connection_start) * 1000
            
            # Execute a simple query
            query_start = time.time()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                query_latency = (time.time() - query_start) * 1000
            
            # Close connection
            conn.close()
            
            total_latency = (time.time() - start_time) * 1000
            
            if result and result[0] == 1:
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.CONNECTED,
                    latency_ms=total_latency,
                    details={
                        "url": self._sanitize_url(self.database_url),
                        "connection_latency_ms": round(connection_latency, 2),
                        "query_latency_ms": round(query_latency, 2),
                        "query": "SELECT 1",
                    },
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.ERROR,
                    latency_ms=total_latency,
                    error="Database query test failed",
                )
                
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="PostgreSQL client library not installed",
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_str = str(e)
            
            # Check for common connection errors
            if "connection" in error_str.lower() or "refused" in error_str.lower():
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.DISCONNECTED,
                    latency_ms=latency,
                    error=f"Connection refused: {self._sanitize_error(error_str)}",
                )
            elif "timeout" in error_str.lower():
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.TIMEOUT,
                    latency_ms=latency,
                    error=f"Connection timeout: {self._sanitize_error(error_str)}",
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.ERROR,
                    latency_ms=latency,
                    error=self._sanitize_error(error_str),
                )
    
    def _sanitize_url(self, url: str) -> str:
        """Sanitize database URL for logging."""
        if not url:
            return url
        
        # Remove password from URL
        import re
        pattern = r"://([^:]+):([^@]+)@"
        sanitized = re.sub(pattern, "://\\1:***@", url)
        return sanitized
    
    def _sanitize_error(self, error: str) -> str:
        """Sanitize error message to remove sensitive information."""
        import re
        # Remove potential passwords or tokens
        sensitive_patterns = [
            r"(password[=:]\s*)[^\s,;]+",
            r"(token[=:]\s*)[^\s,;]+",
            r"(secret[=:]\s*)[^\s,;]+",
        ]
        sanitized = error
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, r"\1***", sanitized, flags=re.IGNORECASE)
        return sanitized
