"""Unified HTTP request pipeline for Scalingo APIs.

This module provides both synchronous and asynchronous HTTP clients
for communicating with the Scalingo API. The async client is recommended
for new code to avoid blocking the event loop.
"""
import asyncio
import time
from typing import Any, Dict, Optional, Union

import httpx

from app.config import settings
from app.core.logging import StructuredLogger
from app.domain import ErrorCode, FailureReason, OperationError, OperationResult
from app.domain.value_objects import Region
from app.infrastructure.scalingo.auth_token_provider import AuthTokenProvider

logger = StructuredLogger("scalingo_http")


class ScalingoHTTPClient:
    """
    Synchronous HTTP client for Scalingo API.
    
    This client uses synchronous httpx.Client and blocks the calling thread.
    For non-blocking operations, use AsyncScalingoHTTPClient instead.
    
    Note: This class is kept for backward compatibility. New code should use
    AsyncScalingoHTTPClient for better performance in async contexts.
    """
    
    def __init__(self, token_provider: AuthTokenProvider, timeout_seconds: float = 20.0):
        self._token_provider = token_provider
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = 2

    def request(
        self,
        method: str,
        region: Region,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True,
        attempt: int = 0,
    ) -> OperationResult[Dict[str, Any]]:
        base_url = settings.scalingo_region_urls.get(region.value)
        if not base_url:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.VALIDATION,
                    message=f"Unknown region '{region.value}'",
                    status_code=400,
                )
            )

        try:
            bearer_token = self._token_provider.get_token()
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            }
            with httpx.Client(base_url=base_url, headers=headers, timeout=self._timeout) as client:
                response = client.request(method, endpoint, params=params, json=json_payload)
            response.raise_for_status()

            if response.status_code == 204 or not response.text:
                return OperationResult.ok({})

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return OperationResult.ok(response.json())

            return OperationResult.ok({"raw": response.text})
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            request_id = exc.response.headers.get("x-request-id")
            if status_code == 401 and retry_on_401:
                logger.info("401 from Scalingo API, refreshing token and retrying", endpoint=endpoint)
                self._token_provider.refresh()
                return self.request(
                    method,
                    region,
                    endpoint,
                    params=params,
                    json_payload=json_payload,
                    retry_on_401=False,
                    attempt=attempt + 1,
                )
            if status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                backoff_seconds = 0.35 * (2 ** attempt)
                logger.warning(
                    "Transient status from Scalingo API, retrying",
                    endpoint=endpoint,
                    status_code=status_code,
                    request_id=request_id,
                    backoff_seconds=backoff_seconds,
                )
                time.sleep(backoff_seconds)
                return self.request(
                    method,
                    region,
                    endpoint,
                    params=params,
                    json_payload=json_payload,
                    retry_on_401=retry_on_401,
                    attempt=attempt + 1,
                )
            return OperationResult.fail(self._to_operation_error(exc))
        except httpx.TimeoutException:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message="Scalingo API request timed out",
                    code=ErrorCode.TIMEOUT_ERROR,
                    status_code=504,
                )
            )
        except httpx.HTTPError as exc:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message=f"Scalingo API transport error: {str(exc)}",
                    code=ErrorCode.TRANSIENT_ERROR,
                    status_code=502,
                )
            )
        except Exception as exc:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message=f"Unable to get Scalingo bearer token: {str(exc)}",
                    code=ErrorCode.AUTH_ERROR,
                    status_code=503,
                )
            )

    def _to_operation_error(self, exc: httpx.HTTPStatusError) -> OperationError:
        status_code = exc.response.status_code
        body = exc.response.text
        request_id = exc.response.headers.get("x-request-id")

        if status_code == 401:
            reason = FailureReason.AUTH
            code = ErrorCode.AUTH_ERROR
        elif status_code == 404:
            reason = FailureReason.NOT_FOUND
            code = ErrorCode.RESOURCE_NOT_FOUND
        elif status_code == 409:
            reason = FailureReason.CONFLICT
            code = ErrorCode.RESOURCE_CONFLICT
        elif status_code == 422:
            reason = FailureReason.VALIDATION
            code = ErrorCode.VALIDATION_ERROR
        elif status_code == 429:
            reason = FailureReason.TRANSIENT
            code = ErrorCode.TRANSIENT_ERROR
        elif status_code >= 500:
            reason = FailureReason.TRANSIENT
            code = ErrorCode.SERVICE_UNAVAILABLE
        else:
            reason = FailureReason.UPSTREAM
            code = ErrorCode.UPSTREAM_ERROR

        return OperationError(
            reason=reason,
            message=f"Scalingo API request failed with status {status_code}",
            code=code,
            status_code=status_code,
            details={"response": body, "request_id": request_id},
        )


class AsyncScalingoHTTPClient:
    """
    Asynchronous HTTP client for Scalingo API.
    
    This client uses async httpx.AsyncClient and does not block the event loop.
    Recommended for all new code, especially in async contexts like FastAPI.
    
    Usage:
        client = AsyncScalingoHTTPClient(token_provider)
        result = await client.request("GET", Region.OSC_FR1, "/v1/apps")
        
        # Or use the context manager for automatic cleanup
        async with AsyncScalingoHTTPClient(token_provider) as client:
            result = await client.request("GET", Region.OSC_FR1, "/v1/apps")
    """
    
    def __init__(self, token_provider: AuthTokenProvider, timeout_seconds: float = 20.0, max_retries: int = 2):
        self._token_provider = token_provider
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _get_bearer_token(self) -> str:
        """Get bearer token, refreshing if necessary."""
        return self._token_provider.get_token()
    
    async def request(
        self,
        method: str,
        region: Region,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True,
        attempt: int = 0,
    ) -> OperationResult[Dict[str, Any]]:
        """
        Make an HTTP request to the Scalingo API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            region: Scalingo region
            endpoint: API endpoint path
            params: Query parameters
            json_payload: Request body as JSON
            retry_on_401: Whether to retry on 401 Unauthorized
            attempt: Current attempt number (for retries)
        
        Returns:
            OperationResult containing the response data or error
        """
        base_url = settings.scalingo_region_urls.get(region.value)
        if not base_url:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.VALIDATION,
                    message=f"Unknown region '{region.value}'",
                    code=ErrorCode.VALIDATION_ERROR,
                    status_code=400,
                )
            )

        try:
            bearer_token = await asyncio.to_thread(self._token_provider.get_token)
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            }
            
            # Create client if not already created
            if self._client is None:
                self._client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=self._timeout)
            else:
                # Update base URL if different
                if self._client.base_url != base_url:
                    await self._client.aclose()
                    self._client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=self._timeout)
            
            response = await self._client.request(method, endpoint, params=params, json=json_payload)
            response.raise_for_status()

            if response.status_code == 204 or not response.text:
                return OperationResult.ok({})

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return OperationResult.ok(response.json())

            return OperationResult.ok({"raw": response.text})
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            request_id = exc.response.headers.get("x-request-id")
            
            if status_code == 401 and retry_on_401:
                logger.info("401 from Scalingo API, refreshing token and retrying", endpoint=endpoint)
                await asyncio.to_thread(self._token_provider.refresh)
                return await self.request(
                    method,
                    region,
                    endpoint,
                    params=params,
                    json_payload=json_payload,
                    retry_on_401=False,
                    attempt=attempt + 1,
                )
            
            if status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                backoff_seconds = 0.35 * (2 ** attempt)
                logger.warning(
                    "Transient status from Scalingo API, retrying",
                    endpoint=endpoint,
                    status_code=status_code,
                    request_id=request_id,
                    backoff_seconds=backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                return await self.request(
                    method,
                    region,
                    endpoint,
                    params=params,
                    json_payload=json_payload,
                    retry_on_401=retry_on_401,
                    attempt=attempt + 1,
                )
            
            return OperationResult.fail(self._to_operation_error(exc))
        except httpx.TimeoutException:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message="Scalingo API request timed out",
                    code=ErrorCode.TIMEOUT_ERROR,
                    status_code=504,
                )
            )
        except httpx.HTTPError as exc:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message=f"Scalingo API transport error: {str(exc)}",
                    code=ErrorCode.TRANSIENT_ERROR,
                    status_code=502,
                )
            )
        except Exception as exc:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message=f"Unable to get Scalingo bearer token: {str(exc)}",
                    code=ErrorCode.AUTH_ERROR,
                    status_code=503,
                )
            )
    
    def _to_operation_error(self, exc: httpx.HTTPStatusError) -> OperationError:
        """Convert HTTP status error to OperationError."""
        status_code = exc.response.status_code
        body = exc.response.text
        request_id = exc.response.headers.get("x-request-id")

        if status_code == 401:
            reason = FailureReason.AUTH
            code = ErrorCode.AUTH_ERROR
        elif status_code == 404:
            reason = FailureReason.NOT_FOUND
            code = ErrorCode.RESOURCE_NOT_FOUND
        elif status_code == 409:
            reason = FailureReason.CONFLICT
            code = ErrorCode.RESOURCE_CONFLICT
        elif status_code == 422:
            reason = FailureReason.VALIDATION
            code = ErrorCode.VALIDATION_ERROR
        elif status_code == 429:
            reason = FailureReason.TRANSIENT
            code = ErrorCode.TRANSIENT_ERROR
        elif status_code >= 500:
            reason = FailureReason.TRANSIENT
            code = ErrorCode.SERVICE_UNAVAILABLE
        else:
            reason = FailureReason.UPSTREAM
            code = ErrorCode.UPSTREAM_ERROR

        return OperationError(
            reason=reason,
            message=f"Scalingo API request failed with status {status_code}",
            code=code,
            status_code=status_code,
            details={"response": body, "request_id": request_id},
        )
    
    async def close(self):
        """Close the async client."""
        if self._client:
            await self._client.aclose()
            self._client = None
