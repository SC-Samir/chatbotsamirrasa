"""
Metrics presentation endpoints.

This module provides FastAPI endpoints for application metrics
using the MetricsService.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.services import MetricsService, get_metrics_service

# Create metrics router
router = APIRouter(prefix="/metrics", tags=["metrics"])


def get_metrics_service_dependency() -> MetricsService:
    """Dependency for getting metrics service instance."""
    return get_metrics_service()


@router.get("/", summary="Get Metrics", description="Get application performance and usage metrics.")
async def get_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service_dependency),
) -> Dict[str, Any]:
    """
    Get application metrics.
    
    Returns:
        Dictionary containing:
        - system: System-level metrics (uptime, request counts, errors)
        - counters: Counter metrics
        - gauges: Gauge metrics
        - histograms: Histogram metrics
        - timers: Timer metrics
    """
    metrics_data = await metrics_service.get_metrics()
    return metrics_data


@router.get("/prometheus", summary="Prometheus Metrics", description="Get metrics in Prometheus-compatible format.")
async def get_prometheus_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service_dependency),
) -> Response:
    """
    Get metrics in Prometheus text exposition format.
    
    Returns:
        Plain text response in Prometheus format
    """
    prometheus_data = await metrics_service.get_prometheus_metrics()
    return Response(content=prometheus_data, media_type="text/plain")


@router.get("/stats", summary="Metrics Statistics", description="Get summary statistics for metrics.")
async def get_metrics_stats(
    metrics_service: MetricsService = Depends(get_metrics_service_dependency),
) -> Dict[str, Any]:
    """
    Get summary statistics for all metrics.
    
    Returns:
        Dictionary containing summary statistics for each metric type
    """
    metrics_data = await metrics_service.get_metrics()
    
    stats = {
        "total_metrics": 0,
        "counters": {
            "count": len(metrics_data.get("counters", {})),
            "total_value": sum(
                v.get("value", 0) 
                for v in metrics_data.get("counters", {}).values()
            ),
        },
        "gauges": {
            "count": len(metrics_data.get("gauges", {})),
        },
        "histograms": {
            "count": len(metrics_data.get("histograms", {})),
        },
        "timers": {
            "count": len(metrics_data.get("timers", {})),
        },
        "system": metrics_data.get("system", {}),
    }
    
    stats["total_metrics"] = (
        stats["counters"]["count"] +
        stats["gauges"]["count"] +
        stats["histograms"]["count"] +
        stats["timers"]["count"]
    )
    
    return stats


@router.post("/counters/{name}/increment", summary="Increment Counter", description="Increment a counter metric.")
async def increment_counter(
    name: str,
    value: float = 1.0,
    metrics_service: MetricsService = Depends(get_metrics_service_dependency),
) -> Dict[str, Any]:
    """
    Increment a counter metric.
    
    Args:
        name: Name of the counter
        value: Value to increment by (default: 1.0)
    
    Returns:
        Success status and new counter value
    """
    await metrics_service.increment_counter(name, value)
    
    metrics_data = await metrics_service.get_metrics()
    counter_value = metrics_data.get("counters", {}).get(name, {}).get("value", 0)
    
    return {
        "status": "success",
        "counter": name,
        "value": counter_value,
    }


@router.post("/gauges/{name}/set", summary="Set Gauge", description="Set a gauge metric value.")
async def set_gauge(
    name: str,
    value: float,
    metrics_service: MetricsService = Depends(get_metrics_service_dependency),
) -> Dict[str, Any]:
    """
    Set a gauge metric value.
    
    Args:
        name: Name of the gauge
        value: Value to set
    
    Returns:
        Success status and current value
    """
    await metrics_service.set_gauge(name, value)
    
    return {
        "status": "success",
        "gauge": name,
        "value": value,
    }


@router.post("/reset", summary="Reset Metrics", description="Reset all metrics to their initial state.")
async def reset_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service_dependency),
) -> Dict[str, Any]:
    """
    Reset all metrics.
    
    Returns:
        Success status
    """
    await metrics_service.reset()
    
    return {
        "status": "success",
        "message": "All metrics have been reset",
    }
