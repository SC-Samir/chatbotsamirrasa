"""
Health check presentation endpoints.

This module provides the FastAPI endpoints for health checks,
readiness probes, liveness probes, and metrics.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.health_service import HealthService, get_health_service, reset_health_service

# Create health router
router = APIRouter(prefix="/health", tags=["health"])


def get_health_service_dependency() -> HealthService:
    """Dependency for getting health service instance."""
    return get_health_service()


@router.get("/", summary="Health Check", description="Perform a comprehensive health check of all application dependencies.")
async def health_check(
    health_service: HealthService = Depends(get_health_service_dependency),
) -> Dict[str, Any]:
    """
    Perform a comprehensive health check.
    
    This endpoint checks the health of all application dependencies including:
    - Redis
    - PostgreSQL
    - Scalingo API
    
    Returns:
        Health status with detailed dependency information
    """
    health_status = await health_service.health_check()
    return health_status.to_dict()


@router.get("/ready", summary="Readiness Check", description="Check if the application is ready to receive traffic.")
async def readiness_check(
    health_service: HealthService = Depends(get_health_service_dependency),
) -> Dict[str, Any]:
    """
    Perform a readiness check.
    
    This endpoint checks if all critical dependencies are available.
    The application is considered ready if all critical dependencies
    (Redis, PostgreSQL) are connected.
    
    Returns:
        Readiness status with dependency information
    """
    readiness_status = await health_service.readiness_check()
    return readiness_status.to_dict()


@router.get("/live", summary="Liveness Check", description="Check if the application is alive.")
async def liveness_check(
    health_service: HealthService = Depends(get_health_service_dependency),
) -> Dict[str, Any]:
    """
    Perform a liveness check.
    
    This endpoint provides a simple check to determine if the application
    is alive and able to process requests. Unlike readiness checks,
    liveness doesn't depend on external dependencies.
    
    Returns:
        Liveness status
    """
    liveness_status = await health_service.liveness_check()
    return {
        "status": liveness_status.value,
        "app_name": settings.app_name,
        "version": health_service.version,
    }


@router.get("/metrics", summary="Metrics Endpoint", description="Get application metrics and health statistics.")
async def metrics(
    health_service: HealthService = Depends(get_health_service_dependency),
) -> Dict[str, Any]:
    """
    Get application metrics.
    
    This endpoint provides metrics about the application and its dependencies
    including health status, latency measurements, and error counts.
    
    Returns:
        Application metrics in a structured format
    """
    metrics_data = await health_service.get_metrics()
    return metrics_data


@router.get("/info", summary="Application Info", description="Get application version and configuration information.")
async def app_info(
    health_service: HealthService = Depends(get_health_service_dependency),
) -> Dict[str, str]:
    """
    Get application information.
    
    This endpoint returns version and configuration information about
    the application.
    
    Returns:
        Application name and version
    """
    return health_service.get_version_info()


@router.get("/dependencies/{name}", summary="Check Specific Dependency", description="Check the health of a specific dependency.")
async def check_dependency(
    name: str,
    health_service: HealthService = Depends(get_health_service_dependency),
) -> Dict[str, Any]:
    """
    Check a specific dependency by name.
    
    This endpoint allows checking individual dependencies by name.
    
    Args:
        name: Name of the dependency to check (e.g., 'redis', 'postgres', 'scalingo_api')
        
    Returns:
        Health status of the specified dependency
    """
    result = await health_service.check_dependency(name)
    
    if result is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Dependency '{name}' not found"},
        )
    
    return result.to_dict()
