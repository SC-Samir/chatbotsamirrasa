"""
Unit tests for MetricsService.

Note: These tests were already created in the previous commit e818c06,
but we're adding additional tests for the metrics endpoints.
"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.metrics_service import (
    MetricsService,
    MetricType,
    MetricValue,
    MetricSummary,
    get_metrics_service,
    reset_metrics_service,
)


class TestMetricType(unittest.TestCase):
    """Tests for MetricType enum."""
    
    def test_enum_values(self):
        """Test that enum values are correct."""
        self.assertEqual(MetricType.COUNTER.value, "counter")
        self.assertEqual(MetricType.GAUGE.value, "gauge")
        self.assertEqual(MetricType.HISTOGRAM.value, "histogram")
        self.assertEqual(MetricType.TIMER.value, "timer")


class TestMetricValue(unittest.TestCase):
    """Tests for MetricValue dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        value = MetricValue(
            name="test_counter",
            value=42.0,
            timestamp=1234567890.0,
        )
        
        self.assertEqual(value.name, "test_counter")
        self.assertEqual(value.value, 42.0)
        self.assertEqual(value.timestamp, 1234567890.0)
        self.assertEqual(value.tags, {})
    
    def test_to_dict(self):
        """Test to_dict method."""
        value = MetricValue(
            name="test_counter",
            value=42.0,
            timestamp=1234567890.0,
            tags={"env": "test", "app": "myapp"},
        )
        
        result = value.to_dict()
        
        self.assertEqual(result["name"], "test_counter")
        self.assertEqual(result["value"], 42.0)
        self.assertEqual(result["timestamp"], 1234567890.0)
        self.assertEqual(result["tags"], {"env": "test", "app": "myapp"})


class TestMetricSummary(unittest.TestCase):
    """Tests for MetricSummary dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        summary = MetricSummary(
            name="test_counter",
            type=MetricType.COUNTER,
        )
        
        self.assertEqual(summary.name, "test_counter")
        self.assertEqual(summary.type, MetricType.COUNTER)
        self.assertEqual(summary.count, 0)
        self.assertEqual(summary.sum, 0.0)
        self.assertEqual(summary.min, float('inf'))
        self.assertEqual(summary.max, float('-inf'))
        self.assertEqual(summary.avg, 0.0)
        self.assertEqual(summary.tags, {})
    
    def test_to_dict(self):
        """Test to_dict method."""
        summary = MetricSummary(
            name="test_counter",
            type=MetricType.COUNTER,
            count=10,
            sum=100.0,
            avg=10.0,
            tags={"env": "test"},
        )
        
        result = summary.to_dict()
        
        self.assertEqual(result["name"], "test_counter")
        self.assertEqual(result["type"], "counter")
        self.assertEqual(result["count"], 10)
        self.assertEqual(result["sum"], 100.0)
        self.assertEqual(result["avg"], 10.0)
        self.assertEqual(result["tags"], {"env": "test"})


class TestMetricsService(unittest.IsolatedAsyncioTestCase):
    """Tests for MetricsService."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        await reset_metrics_service()
        self.metrics_service = MetricsService()
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        await reset_metrics_service()
    
    async def test_increment_counter(self):
        """Test incrementing a counter."""
        await self.metrics_service.increment_counter("test_counter", 1.0)
        await self.metrics_service.increment_counter("test_counter", 2.0)
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertIn("test_counter", metrics["counters"])
        self.assertEqual(metrics["counters"]["test_counter"]["value"], 3.0)
    
    async def test_set_gauge(self):
        """Test setting a gauge."""
        await self.metrics_service.set_gauge("test_gauge", 42.0)
        await self.metrics_service.set_gauge("test_gauge", 100.0)
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertIn("test_gauge", metrics["gauges"])
        self.assertEqual(metrics["gauges"]["test_gauge"]["values"][""], 100.0)
    
    async def test_record_histogram(self):
        """Test recording histogram values."""
        await self.metrics_service.record_histogram("test_histogram", 10.0)
        await self.metrics_service.record_histogram("test_histogram", 20.0)
        await self.metrics_service.record_histogram("test_histogram", 30.0)
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertIn("test_histogram", metrics["histograms"])
        self.assertEqual(metrics["histograms"]["test_histogram"]["count"], 3)
        self.assertEqual(metrics["histograms"]["test_histogram"]["sum"], 60.0)
        self.assertEqual(metrics["histograms"]["test_histogram"]["avg"], 20.0)
        self.assertEqual(metrics["histograms"]["test_histogram"]["min"], 10.0)
        self.assertEqual(metrics["histograms"]["test_histogram"]["max"], 30.0)
    
    async def test_record_timer(self):
        """Test recording timer durations."""
        await self.metrics_service.record_timer("test_timer", 0.1)
        await self.metrics_service.record_timer("test_timer", 0.2)
        await self.metrics_service.record_timer("test_timer", 0.3)
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertIn("test_timer", metrics["timers"])
        self.assertEqual(metrics["timers"]["test_timer"]["count"], 3)
        self.assertAlmostEqual(metrics["timers"]["test_timer"]["sum"], 0.6, places=5)
        self.assertAlmostEqual(metrics["timers"]["test_timer"]["avg"], 0.2, places=5)
    
    async def test_record_request(self):
        """Test recording requests."""
        await self.metrics_service.record_request(0.1, success=True)
        await self.metrics_service.record_request(0.2, success=True)
        await self.metrics_service.record_request(0.3, success=False)
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertEqual(metrics["system"]["requests_total"], 3)
        self.assertEqual(metrics["system"]["errors_total"], 1)
        self.assertAlmostEqual(metrics["system"]["request_avg_time"], 0.2, places=5)
    
    async def test_get_metric_summary(self):
        """Test getting metric summary."""
        await self.metrics_service.increment_counter("test_counter", 10.0)
        
        summary = await self.metrics_service.get_metric_summary("test_counter", MetricType.COUNTER)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary.name, "test_counter")
        self.assertEqual(summary.type, MetricType.COUNTER)
    
    async def test_get_prometheus_metrics(self):
        """Test getting metrics in Prometheus format."""
        await self.metrics_service.increment_counter("test_counter", 1.0)
        await self.metrics_service.set_gauge("test_gauge", 42.0)
        
        prometheus_data = await self.metrics_service.get_prometheus_metrics()
        
        self.assertIsInstance(prometheus_data, str)
        self.assertIn("test_counter", prometheus_data)
        self.assertIn("test_gauge", prometheus_data)
        self.assertIn("TYPE", prometheus_data)
        self.assertIn("HELP", prometheus_data)
    
    async def test_reset(self):
        """Test resetting metrics."""
        await self.metrics_service.increment_counter("test_counter", 1.0)
        await self.metrics_service.set_gauge("test_gauge", 42.0)
        
        await self.metrics_service.reset()
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertEqual(metrics["system"]["requests_total"], 0)
        self.assertEqual(metrics["system"]["errors_total"], 0)
        self.assertEqual(len(metrics["counters"]), 0)
        self.assertEqual(len(metrics["gauges"]), 0)
    
    async def test_tags_support(self):
        """Test that tags are properly stored and retrieved."""
        await self.metrics_service.increment_counter("test_counter", 1.0, tags={"env": "test", "app": "myapp"})
        
        metrics = await self.metrics_service.get_metrics()
        
        self.assertIn("test_counter", metrics["counters"])
        self.assertEqual(metrics["counters"]["test_counter"]["tags"], ["env=test,app=myapp"])


class TestSingletonFunctions(unittest.IsolatedAsyncioTestCase):
    """Tests for singleton functions."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        await reset_metrics_service()
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        await reset_metrics_service()
    
    async def test_get_metrics_service_singleton(self):
        """Test that get_metrics_service returns the same instance."""
        service1 = await get_metrics_service()
        service2 = await get_metrics_service()
        
        self.assertIs(service1, service2)
    
    async def test_reset_metrics_service(self):
        """Test resetting the metrics service."""
        service1 = await get_metrics_service()
        await reset_metrics_service()
        service2 = await get_metrics_service()
        
        self.assertIsNot(service1, service2)


if __name__ == "__main__":
    unittest.main()
