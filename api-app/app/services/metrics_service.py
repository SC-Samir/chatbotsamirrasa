"""
Metrics and performance monitoring service.

This module provides metrics collection, tracking, and reporting for
the application, including:
- Request metrics
- Response time tracking
- Error tracking
- Resource usage monitoring
- Custom metrics
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import asyncio

from app.core.logging import StructuredLogger

logger = StructuredLogger("metrics_service")


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """A single metric value."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


@dataclass
class MetricSummary:
    """Summary of a metric."""
    name: str
    type: MetricType
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    avg: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "type": self.type.value,
            "count": self.count,
            "sum": self.sum,
            "avg": self.avg if self.count > 0 else 0,
            "tags": self.tags,
        }
        if self.min != float('inf'):
            result["min"] = self.min
        if self.max != float('-inf'):
            result["max"] = self.max
        return result


class MetricsService:
    """
    Service for collecting and reporting application metrics.
    
    Supports:
    - Counter metrics (incrementing values)
    - Gauge metrics (current values)
    - Histogram metrics (distribution of values)
    - Timer metrics (duration tracking)
    - Custom metrics
    """
    
    def __init__(self):
        # Metric storage
        self._counters: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        # Request metrics
        self._request_count: int = 0
        self._request_times: List[float] = []
        self._error_count: int = 0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Start time
        self._start_time = time.time()
    
    async def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        tags = tags or {}
        async with self._lock:
            key = self._make_key(name, tags)
            self._counters[name][key] = self._counters[name].get(key, 0) + value
    
    async def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        tags = tags or {}
        async with self._lock:
            key = self._make_key(name, tags)
            self._gauges[name][key] = value
    
    async def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a value in a histogram."""
        async with self._lock:
            self._histograms[name].append(value)
            # Keep only last 1000 values
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]
    
    async def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer duration."""
        async with self._lock:
            self._timers[name].append(duration)
            # Keep only last 1000 values
            if len(self._timers[name]) > 1000:
                self._timers[name] = self._timers[name][-1000:]
    
    async def record_request(self, duration: float, success: bool = True) -> None:
        """Record a request metric."""
        async with self._lock:
            self._request_count += 1
            self._request_times.append(duration)
            
            # Keep only last 1000 requests
            if len(self._request_times) > 1000:
                self._request_times = self._request_times[-1000:]
            
            if not success:
                self._error_count += 1
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        async with self._lock:
            metrics = {
                "system": {
                    "uptime": time.time() - self._start_time,
                    "requests_total": self._request_count,
                    "errors_total": self._error_count,
                },
                "counters": {},
                "gauges": {},
                "histograms": {},
                "timers": {},
            }
            
            # Add request metrics
            if self._request_times:
                avg_time = sum(self._request_times) / len(self._request_times)
                metrics["system"]["request_avg_time"] = avg_time
                metrics["system"]["request_min_time"] = min(self._request_times)
                metrics["system"]["request_max_time"] = max(self._request_times)
            
            # Add counters
            for name, values in self._counters.items():
                metrics["counters"][name] = {
                    "value": sum(values.values()),
                    "tags": list(values.keys()),
                }
            
            # Add gauges
            for name, values in self._gauges.items():
                metrics["gauges"][name] = {
                    "values": values,
                }
            
            # Add histograms
            for name, values in self._histograms.items():
                if values:
                    metrics["histograms"][name] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                    }
            
            # Add timers
            for name, values in self._timers.items():
                if values:
                    metrics["timers"][name] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                    }
            
            return metrics
    
    async def get_metric_summary(self, name: str, metric_type: MetricType) -> Optional[MetricSummary]:
        """Get a summary for a specific metric."""
        async with self._lock:
            if metric_type == MetricType.COUNTER:
                values = self._counters.get(name, {})
                if not values:
                    return None
                return MetricSummary(
                    name=name,
                    type=metric_type,
                    count=len(values),
                    sum=sum(values.values()),
                    avg=sum(values.values()) / len(values) if values else 0,
                )
            elif metric_type == MetricType.GAUGE:
                values = self._gauges.get(name, {})
                if not values:
                    return None
                return MetricSummary(
                    name=name,
                    type=metric_type,
                    count=len(values),
                    sum=sum(values.values()),
                    avg=sum(values.values()) / len(values) if values else 0,
                )
            elif metric_type == MetricType.HISTOGRAM:
                values = self._histograms.get(name, [])
                if not values:
                    return None
                return MetricSummary(
                    name=name,
                    type=metric_type,
                    count=len(values),
                    sum=sum(values),
                    min=min(values),
                    max=max(values),
                    avg=sum(values) / len(values),
                )
            elif metric_type == MetricType.TIMER:
                values = self._timers.get(name, [])
                if not values:
                    return None
                return MetricSummary(
                    name=name,
                    type=metric_type,
                    count=len(values),
                    sum=sum(values),
                    min=min(values),
                    max=max(values),
                    avg=sum(values) / len(values),
                )
        return None
    
    async def reset(self) -> None:
        """Reset all metrics."""
        async with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._request_count = 0
            self._request_times.clear()
            self._error_count = 0
            self._start_time = time.time()
    
    async def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        async with self._lock:
            lines = []
            
            # System metrics
            lines.append(f"# HELP system_uptime Uptime in seconds")
            lines.append(f"# TYPE system_uptime gauge")
            lines.append(f"system_uptime {time.time() - self._start_time}")
            
            lines.append(f"# HELP system_requests_total Total requests")
            lines.append(f"# TYPE system_requests_total counter")
            lines.append(f"system_requests_total {self._request_count}")
            
            lines.append(f"# HELP system_errors_total Total errors")
            lines.append(f"# TYPE system_errors_total counter")
            lines.append(f"system_errors_total {self._error_count}")
            
            if self._request_times:
                avg_time = sum(self._request_times) / len(self._request_times)
                lines.append(f"# HELP system_request_avg_time Average request time")
                lines.append(f"# TYPE system_request_avg_time gauge")
                lines.append(f"system_request_avg_time {avg_time}")
            
            # Counter metrics
            for name, values in self._counters.items():
                total = sum(values.values())
                lines.append(f"# HELP {name} {name}")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {total}")
            
            # Gauge metrics
            for name, values in self._gauges.items():
                for key, value in values.items():
                    tags = key.replace(",", ";").replace("=", ":")
                    lines.append(f"# HELP {name} {name}")
                    lines.append(f"# TYPE {name} gauge")
                    if tags:
                        lines.append(f"{name}{{{tags}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
            
            # Timer metrics
            for name, values in self._timers.items():
                if values:
                    avg = sum(values) / len(values)
                    lines.append(f"# HELP {name}_avg {name} average")
                    lines.append(f"# TYPE {name}_avg gauge")
                    lines.append(f"{name}_avg {avg}")
                    
                    lines.append(f"# HELP {name}_count {name} count")
                    lines.append(f"# TYPE {name}_count counter")
                    lines.append(f"{name}_count {len(values)}")
            
            return "\n".join(lines)
    
    @staticmethod
    def _make_key(name: str, tags: Dict[str, str]) -> str:
        """Make a unique key from name and tags."""
        if not tags:
            return name
        tag_pairs = [f"{k}={v}" for k, v in sorted(tags.items())]
        return f"{name}:{','.join(tag_pairs)}"


# Singleton instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get or create the singleton metrics service."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def reset_metrics_service() -> None:
    """Reset the singleton metrics service (useful for testing)."""
    global _metrics_service
    if _metrics_service:
        _metrics_service = None
