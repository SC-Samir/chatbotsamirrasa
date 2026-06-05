"""
Unit tests for health service and health checkers.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone

from app.infrastructure.health.health_checker import (
    HealthChecker,
    HealthCheckResult,
    HealthCheckerInterface,
    HealthStatus,
    DependencyStatus,
    AggregateHealthStatus,
)
from app.infrastructure.health.redis_health import RedisHealthChecker
from app.infrastructure.health.postgres_health import PostgresHealthChecker
from app.infrastructure.health.scalingo_health import ScalingoHealthChecker
from app.services.health_service import HealthService


class MockHealthChecker(HealthCheckerInterface):
    """Mock health checker for testing."""
    
    def __init__(self, name: str, status: DependencyStatus, should_fail: bool = False):
        self._name = name
        self._status = status
        self._should_fail = should_fail
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> HealthCheckResult:
        if self._should_fail:
            raise Exception("Mock error")
        return HealthCheckResult(
            name=self._name,
            status=self._status,
            latency_ms=10.0,
        )


@pytest.mark.asyncio
class TestHealthChecker:
    """Tests for HealthChecker class."""
    
    async def test_health_checker_with_all_passing(self):
        """Test health checker when all checkers pass."""
        checker = HealthChecker(
            app_name="test_app",
            version="1.0.0",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.CONNECTED),
                MockHealthChecker("postgres", DependencyStatus.CONNECTED),
            ],
        )
        
        result = await checker.check_all()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.checks_performed == 2
        assert result.checks_passed == 2
        assert result.checks_failed == 0
        assert len(result.dependencies) == 2
        assert "redis" in result.dependencies
        assert "postgres" in result.dependencies
    
    async def test_health_checker_with_some_failing(self):
        """Test health checker when some checkers fail."""
        checker = HealthChecker(
            app_name="test_app",
            version="1.0.0",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.CONNECTED),
                MockHealthChecker("postgres", DependencyStatus.ERROR),
            ],
        )
        
        result = await checker.check_all()
        
        assert result.status == HealthStatus.DEGRADED
        assert result.checks_performed == 2
        assert result.checks_passed == 1
        assert result.checks_failed == 1
    
    async def test_health_checker_with_all_failing(self):
        """Test health checker when all checkers fail."""
        checker = HealthChecker(
            app_name="test_app",
            version="1.0.0",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.ERROR),
                MockHealthChecker("postgres", DependencyStatus.ERROR),
            ],
        )
        
        result = await checker.check_all()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.checks_performed == 2
        assert result.checks_passed == 0
        assert result.checks_failed == 2
    
    async def test_health_checker_with_checker_exception(self):
        """Test health checker when a checker raises an exception."""
        checker = HealthChecker(
            app_name="test_app",
            version="1.0.0",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.CONNECTED),
                MockHealthChecker("postgres", DependencyStatus.CONNECTED, should_fail=True),
            ],
        )
        
        result = await checker.check_all()
        
        assert result.status == HealthStatus.DEGRADED
        assert result.checks_performed == 2
        assert result.checks_passed == 1
        assert result.checks_failed == 1
        assert result.dependencies["postgres"].status == DependencyStatus.ERROR
    
    async def test_check_component(self):
        """Test checking a specific component."""
        checker = HealthChecker(
            app_name="test_app",
            version="1.0.0",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.CONNECTED),
                MockHealthChecker("postgres", DependencyStatus.ERROR),
            ],
        )
        
        result = await checker.check_component("redis")
        assert result is not None
        assert result.name == "redis"
        assert result.status == DependencyStatus.CONNECTED
        
        result = await checker.check_component("nonexistent")
        assert result is None


class TestHealthCheckResult:
    """Tests for HealthCheckResult."""
    
    def test_to_dict_basic(self):
        """Test basic to_dict conversion."""
        result = HealthCheckResult(
            name="test",
            status=DependencyStatus.CONNECTED,
        )
        
        data = result.to_dict()
        
        assert data["name"] == "test"
        assert data["status"] == "connected"
        assert "timestamp" in data
    
    def test_to_dict_with_latency(self):
        """Test to_dict with latency."""
        result = HealthCheckResult(
            name="test",
            status=DependencyStatus.CONNECTED,
            latency_ms=15.5,
        )
        
        data = result.to_dict()
        
        assert data["latency_ms"] == 15.5
    
    def test_to_dict_with_error(self):
        """Test to_dict with error."""
        result = HealthCheckResult(
            name="test",
            status=DependencyStatus.ERROR,
            error="Connection refused",
        )
        
        data = result.to_dict()
        
        assert data["error"] == "Connection refused"
    
    def test_to_dict_with_details(self):
        """Test to_dict with details."""
        result = HealthCheckResult(
            name="test",
            status=DependencyStatus.CONNECTED,
            details={"url": "localhost", "operations": ["ping"]},
        )
        
        data = result.to_dict()
        
        assert data["details"] == {"url": "localhost", "operations": ["ping"]}


class TestAggregateHealthStatus:
    """Tests for AggregateHealthStatus."""
    
    def test_to_dict(self):
        """Test to_dict conversion."""
        health_result = HealthCheckResult(
            name="redis",
            status=DependencyStatus.CONNECTED,
            latency_ms=10.0,
        )
        
        status = AggregateHealthStatus(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            app_name="test_app",
            timestamp=datetime.now(timezone.utc).isoformat(),
            dependencies={"redis": health_result},
            checks_performed=1,
            checks_passed=1,
            checks_failed=0,
        )
        
        data = status.to_dict()
        
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["app_name"] == "test_app"
        assert data["summary"]["checks_performed"] == 1
        assert "dependencies" in data
        assert "redis" in data["dependencies"]


@pytest.mark.asyncio
class TestRedisHealthChecker:
    """Tests for RedisHealthChecker."""
    
    async def test_redis_not_configured(self):
        """Test Redis health checker when URL is not configured."""
        with patch("app.infrastructure.health.redis_health.settings") as mock_settings:
            mock_settings.redis_url = None
            
            checker = RedisHealthChecker()
            result = await checker.check()
            
            assert result.status == DependencyStatus.DISCONNECTED
            assert result.error == "Redis URL not configured"
    
    async def test_redis_import_error(self):
        """Test Redis health checker when redis library is not installed."""
        with patch("app.infrastructure.health.redis_health.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"
            
            with patch.dict("sys.modules", {"redis": None, "redis.asyncio": None}):
                # Need to import after mocking sys.modules
                import importlib
                import sys
                # Temporarily remove redis from sys.modules
                old_redis = sys.modules.get("redis")
                old_redis_asyncio = sys.modules.get("redis.asyncio")
                sys.modules["redis"] = None
                sys.modules["redis.asyncio"] = None
                
                try:
                    checker = RedisHealthChecker()
                    result = await checker.check()
                    
                    assert result.status == DependencyStatus.DISCONNECTED
                    assert "not installed" in result.error
                finally:
                    # Restore original modules
                    if old_redis is not None:
                        sys.modules["redis"] = old_redis
                    else:
                        del sys.modules["redis"]
                    if old_redis_asyncio is not None:
                        sys.modules["redis.asyncio"] = old_redis_asyncio
                    else:
                        del sys.modules["redis.asyncio"]


@pytest.mark.asyncio
class TestPostgresHealthChecker:
    """Tests for PostgresHealthChecker."""
    
    async def test_postgres_not_configured(self):
        """Test PostgreSQL health checker when URL is not configured."""
        with patch("app.infrastructure.health.postgres_health.settings") as mock_settings:
            mock_settings.database_url = None
            mock_settings.memory_postgres_dsn = None
            
            checker = PostgresHealthChecker()
            result = await checker.check()
            
            assert result.status == DependencyStatus.DISCONNECTED
            assert result.error == "PostgreSQL URL not configured"
    
    async def test_postgres_import_error(self):
        """Test PostgreSQL health checker when psycopg is not installed."""
        with patch("app.infrastructure.health.postgres_health.settings") as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            
            with patch.dict("sys.modules", {"psycopg": None}):
                import sys
                # Temporarily remove psycopg from sys.modules
                old_psycopg = sys.modules.get("psycopg")
                sys.modules["psycopg"] = None
                
                try:
                    checker = PostgresHealthChecker()
                    result = await checker.check()
                    
                    assert result.status == DependencyStatus.DISCONNECTED
                    assert "not installed" in result.error
                finally:
                    # Restore original modules
                    if old_psycopg is not None:
                        sys.modules["psycopg"] = old_psycopg
                    else:
                        del sys.modules["psycopg"]


class TestHealthService:
    """Tests for HealthService."""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check with mock checkers."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.app_name = "test_app"
            
            service = HealthService(
                app_name="test_app",
                version="1.0.0",
                checkers=[
                    MockHealthChecker("redis", DependencyStatus.CONNECTED),
                    MockHealthChecker("postgres", DependencyStatus.CONNECTED),
                ],
            )
            
            result = await service.health_check()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.app_name == "test_app"
            assert result.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_liveness_check(self):
        """Test liveness check always returns healthy."""
        service = HealthService()
        
        result = await service.liveness_check()
        
        assert result == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_readiness_check_with_all_connected(self):
        """Test readiness check when all critical dependencies are connected."""
        service = HealthService(
            app_name="test_app",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.CONNECTED),
                MockHealthChecker("postgres", DependencyStatus.CONNECTED),
            ],
        )
        
        result = await service.readiness_check()
        
        assert result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_readiness_check_with_critical_disconnected(self):
        """Test readiness check when critical dependencies are not connected."""
        service = HealthService(
            app_name="test_app",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.DISCONNECTED),
                MockHealthChecker("postgres", DependencyStatus.CONNECTED),
            ],
        )
        
        result = await service.readiness_check()
        
        assert result.status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test metrics endpoint."""
        service = HealthService(
            app_name="test_app",
            checkers=[
                MockHealthChecker("redis", DependencyStatus.CONNECTED, should_fail=False),
            ],
        )
        
        metrics = await service.get_metrics()
        
        assert "health" in metrics
        assert "dependencies" in metrics
        assert metrics["health"]["status"] == "healthy"
    
    def test_get_version_info(self):
        """Test version info endpoint."""
        service = HealthService(app_name="test_app", version="1.0.0")
        
        info = service.get_version_info()
        
        assert info["app_name"] == "test_app"
        assert info["version"] == "1.0.0"
