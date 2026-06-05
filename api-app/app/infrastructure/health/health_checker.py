"""
Base health checker module.

This module provides the base classes and interfaces for health checking
dependencies and services.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthStatus(str, Enum):
    """Overall health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DependencyStatus(str, Enum):
    """Individual dependency status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: DependencyStatus
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.error:
            result["error"] = self.error
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class AggregateHealthStatus:
    """Aggregate health status for all dependencies."""
    status: HealthStatus
    version: str
    app_name: str
    timestamp: str
    components: Dict[str, HealthCheckResult] = field(default_factory=dict)
    dependencies: Dict[str, HealthCheckResult] = field(default_factory=dict)
    checks_performed: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "version": self.version,
            "app_name": self.app_name,
            "timestamp": self.timestamp,
            "summary": {
                "checks_performed": self.checks_performed,
                "checks_passed": self.checks_passed,
                "checks_failed": self.checks_failed,
            },
            "components": {name: result.to_dict() for name, result in self.components.items()},
            "dependencies": {name: result.to_dict() for name, result in self.dependencies.items()},
        }


class HealthCheckerInterface(ABC):
    """Abstract base class for health checkers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the health checker."""
        pass
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Perform the health check."""
        pass


class HealthChecker:
    """
    Main health checker that aggregates results from multiple checkers.
    
    This class coordinates health checks across all registered dependencies
    and provides aggregate status information.
    """
    
    def __init__(
        self,
        app_name: str,
        version: str,
        checkers: List[HealthCheckerInterface] = None,
    ):
        self.app_name = app_name
        self.version = version
        self.checkers: Dict[str, HealthCheckerInterface] = {}
        
        if checkers:
            for checker in checkers:
                self.register_checker(checker)
    
    def register_checker(self, checker: HealthCheckerInterface) -> None:
        """Register a health checker."""
        self.checkers[checker.name] = checker
    
    async def check_all(self) -> AggregateHealthStatus:
        """
        Perform all health checks and return aggregate status.
        
        Returns:
            AggregateHealthStatus with results from all checkers
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        results: Dict[str, HealthCheckResult] = {}
        
        checks_performed = 0
        checks_passed = 0
        checks_failed = 0
        
        for name, checker in self.checkers.items():
            try:
                result = await checker.check()
                results[name] = result
                checks_performed += 1
                
                if result.status in [DependencyStatus.CONNECTED, DependencyStatus.UNKNOWN]:
                    checks_passed += 1
                else:
                    checks_failed += 1
            except Exception as e:
                # If the checker itself fails, mark it as error
                results[name] = HealthCheckResult(
                    name=name,
                    status=DependencyStatus.ERROR,
                    error=str(e),
                )
                checks_performed += 1
                checks_failed += 1
        
        # Determine overall status
        if checks_failed == 0:
            status = HealthStatus.HEALTHY
        elif checks_failed < checks_performed:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return AggregateHealthStatus(
            status=status,
            version=self.version,
            app_name=self.app_name,
            timestamp=timestamp,
            dependencies=results,
            checks_performed=checks_performed,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )
    
    async def check_component(self, name: str) -> Optional[HealthCheckResult]:
        """
        Perform a specific health check by name.
        
        Args:
            name: Name of the checker to run
            
        Returns:
            HealthCheckResult or None if checker not found
        """
        checker = self.checkers.get(name)
        if checker is None:
            return None
        return await checker.check()
