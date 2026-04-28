"""Unified HTTP request pipeline for Scalingo APIs."""
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.logging import StructuredLogger
from app.domain import FailureReason, OperationError, OperationResult
from app.domain.value_objects import Region
from app.infrastructure.scalingo.auth_token_provider import AuthTokenProvider

logger = StructuredLogger("scalingo_http")


class ScalingoHTTPClient:
    def __init__(self, token_provider: AuthTokenProvider, timeout_seconds: float = 20.0):
        self._token_provider = token_provider
        self._timeout = httpx.Timeout(timeout_seconds)

    def request(
        self,
        method: str,
        region: Region,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True,
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
                )
            return OperationResult.fail(self._to_operation_error(exc))
        except httpx.TimeoutException:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message="Scalingo API request timed out",
                    status_code=504,
                )
            )
        except httpx.HTTPError as exc:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message=f"Scalingo API transport error: {str(exc)}",
                    status_code=502,
                )
            )
        except Exception as exc:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.TRANSIENT,
                    message=f"Unable to get Scalingo bearer token: {str(exc)}",
                    status_code=503,
                )
            )

    def _to_operation_error(self, exc: httpx.HTTPStatusError) -> OperationError:
        status_code = exc.response.status_code
        body = exc.response.text

        if status_code == 401:
            reason = FailureReason.AUTH
        elif status_code == 404:
            reason = FailureReason.NOT_FOUND
        elif status_code == 409:
            reason = FailureReason.CONFLICT
        elif status_code == 422:
            reason = FailureReason.VALIDATION
        elif status_code >= 500:
            reason = FailureReason.TRANSIENT
        else:
            reason = FailureReason.UPSTREAM

        return OperationError(
            reason=reason,
            message=f"Scalingo API request failed with status {status_code}",
            status_code=status_code,
            details={"response": body},
        )
