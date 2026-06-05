"""
Health service module.

This module provides the health check service that coordinates
health checks across all application dependencies.
"""
from typing import Any, Dict, List, Optional

from app.config import settings
from app.infrastructure.health.health_checker import (
    AggregateHealthStatus,
    HealthCheckResult,
    HealthChecker,
    HealthCheckerInterface,
    HealthStatus,
    DependencyStatus,
)
from app.infrastructure.health.redis_health import RedisHealthChecker
from app.infrastructure.health.postgres_health import PostgresHealthChecker
from app.infrastructure.health.scalingo_health import ScalingoHealthChecker


class HealthService:
    """
    Service for managing health checks across all application dependencies.
    
    This service provides:
    - Health check coordination
    - Status aggregation
    - Individual dependency checks
    - Readiness and liveness probes
    """
    
    def __init__(
        self,
        app_name: Optional[str] = None,
        version: Optional[str] = None,
        checkers: Optional[List[HealthCheckerInterface]] = None,
    ):
        self.app_name = app_name or settings.app_name
        self.version = version or getattr(settings, 'version', 'unknown') or self._get_app_version()
        self.health_checker = HealthChecker(
            app_name=self.app_name,
            version=self.version,
            checkers=checkers,
        )
        
        # Register default checkers
        if checkers is None:
            self._register_default_checkers()
    
    def _get_app_version(self) -> str:
        """Try to get application version from various sources."""
        try:
            # Try to import from main module
            from app import main
            if hasattr(main, 'app') and hasattr(main.app, 'version'):
                return main.app.version
        except Exception:
            pass
        return "unknown"
    
    def _register_default_checkers(self) -> None:
        """Register the default health checkers."""
        # Redis checker
        redis_checker = RedisHealthChecker()
        self.health_checker.register_checker(redis_checker)
        
        # PostgreSQL checker
        postgres_checker = PostgresHealthChecker()
        self.health_checker.register_checker(postgres_checker)
        
        # Scalingo API checker
        scalingo_checker = ScalingoHealthChecker()
        self.health_checker.register_checker(scalingo_checker)
    
    async def health_check(self) -> AggregateHealthStatus:
        """
        Perform a comprehensive health check.
        
        Returns:
            AggregateHealthStatus with results from all checkers
        """
        return await self.health_checker.check_all()
    
    async def readiness_check(self) -> AggregateHealthStatus:
        """
        Perform a readiness check.
        
        This is similar to health check but may have different criteria
        for determining if the application is ready to receive traffic.
        
        Returns:
            AggregateHealthStatus indicating readiness
        """
        # For readiness, we want all critical dependencies to be connected
        status = await self.health_checker.check_all()
        
        # Check if critical dependencies are ready
        critical_deps = ['redis', 'postgres']
        all_ready = True
        
        for dep_name in critical_deps:
            if dep_name in status.dependencies:
                dep = status.dependencies[dep_name]
                if dep.status != DependencyStatus.CONNECTED:
                    all_ready = False
                    break
        
        # Override status based on readiness
        if all_ready and status.status == HealthStatus.HEALTHY:
            status.status = HealthStatus.HEALTHY
        elif not all_ready:
            status.status = HealthStatus.DEGRADED
        
        return status
    
    async def liveness_check(self) -> HealthStatus:
        """
        Perform a liveness check.
        
        This is a simple check to determine if the application is alive.
        Unlike readiness, liveness doesn't depend on external dependencies.
        
        Returns:
            HealthStatus indicating liveness
        """
        # For liveness, we just need to be able to respond
        # The application is alive if it can process requests
        return HealthStatus.HEALTHY
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get application metrics.
        
        Returns:
            Dictionary with application metrics
        """
        # Get health status
        health = await self.health_check()
        
        # Build metrics response
        metrics = {
            "health": {
                "status": health.status.value,
                "checks_performed": health.checks_performed,
                "checks_passed": health.checks_passed,
                "checks_failed": health.checks_failed,
            },
            "dependencies": {},
        }
        
        # Add dependency metrics
        for name, result in health.dependencies.items():
            metrics["dependencies"][name] = {
                "status": result.status.value,
                "latency_ms": result.latency_ms,
                "error": result.error or "",
            }
        
        return metrics
    
    async def check_dependency(self, name: str) -> Optional[HealthCheckResult]:
        """
        Check a specific dependency by name.
        
        Args:
            name: Name of the dependency to check
            
        Returns:
            HealthCheckResult or None if dependency not found
        """
        return await self.health_checker.check_component(name)
    
    def get_version_info(self) -> Dict[str, str]:
        """
        Get version information.
        
        Returns:
            Dictionary with version info
        """
        return {
            "app_name": self.app_name,
            "version": self.version,
        }


# Singleton instance
_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    """
    Get or create the singleton health service instance.
    
    Returns:
        HealthService instance
    """
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service


def reset_health_service() -> None:
    """Reset the singleton health service instance (useful for testing)."""
    global _health_service
    _health_service = None
