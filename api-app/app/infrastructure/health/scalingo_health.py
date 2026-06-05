"""
Scalingo API health checker module.

This module provides health checking for Scalingo API connectivity.
"""
import time
from typing import Any, Optional

from app.config import settings
from app.infrastructure.health.health_checker import (
    HealthCheckResult,
    HealthCheckerInterface,
    DependencyStatus,
)
from app.infrastructure.scalingo import ScalingoHTTPClient, build_default_token_provider


class ScalingoHealthChecker(HealthCheckerInterface):
    """
    Health checker for Scalingo API connectivity.
    
    Checks connectivity to configured Scalingo regions.
    """
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        region_urls: Optional[dict] = None,
    ):
        self.api_token = api_token or settings.scalingo_api_token
        self.region_urls = region_urls or settings.scalingo_region_urls
        self._name = "scalingo_api"
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> HealthCheckResult:
        """
        Perform Scalingo API health check.
        
        Returns:
            HealthCheckResult with connection status and latency
        """
        start_time = time.time()
        
        if not self.api_token:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="Scalingo API token not configured",
            )
        
        if not self.region_urls:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="No Scalingo region URLs configured",
            )
        
        try:
            token_provider = build_default_token_provider()
            client = ScalingoHTTPClient(token_provider)
            
            # Test connectivity to all regions
            region_statuses = {}
            total_latency = 0
            successful_regions = 0
            
            for region_name, region_url in self.region_urls.items():
                region_start = time.time()
                try:
                    # Try to make a simple API call (GET /apps)
                    response = await client.request(
                        method="GET",
                        url=f"{region_url}/v1/apps",
                        params={"limit": 1},
                        timeout=5.0,
                    )
                    region_latency = (time.time() - region_start) * 1000
                    
                    if response.status_code in [200, 401, 403]:
                        # 200 means success, 401/403 means auth is working
                        region_statuses[region_name] = {
                            "status": "connected",
                            "latency_ms": round(region_latency, 2),
                            "http_status": response.status_code,
                        }
                        successful_regions += 1
                    else:
                        region_statuses[region_name] = {
                            "status": "error",
                            "latency_ms": round(region_latency, 2),
                            "http_status": response.status_code,
                            "error": f"Unexpected status code: {response.status_code}",
                        }
                except Exception as e:
                    region_latency = (time.time() - region_start) * 1000
                    error_str = str(e)
                    region_statuses[region_name] = {
                        "status": "error",
                        "latency_ms": round(region_latency, 2),
                        "error": error_str[:200],  # Truncate long errors
                    }
            
            total_latency = (time.time() - start_time) * 1000
            
            if successful_regions > 0:
                status = DependencyStatus.CONNECTED
                error = None
            elif successful_regions == 0 and len(self.region_urls) > 0:
                status = DependencyStatus.ERROR
                error = "No regions responded successfully"
            else:
                status = DependencyStatus.DISCONNECTED
                error = "No regions configured"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                latency_ms=total_latency,
                error=error,
                details={
                    "regions": region_statuses,
                    "total_regions": len(self.region_urls),
                    "successful_regions": successful_regions,
                    "test_endpoint": "/v1/apps",
                },
            )
                
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=DependencyStatus.DISCONNECTED,
                error="Scalingo HTTP client not available",
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_str = str(e)
            
            if "timeout" in error_str.lower():
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.TIMEOUT,
                    latency_ms=latency,
                    error=f"API request timeout: {error_str[:200]}",
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=DependencyStatus.ERROR,
                    latency_ms=latency,
                    error=f"API check failed: {error_str[:200]}",
                )
