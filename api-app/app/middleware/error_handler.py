"""
Middleware for centralized error handling.

This middleware catches and formats all exceptions consistently,
providing structured error responses with proper HTTP status codes.
"""
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions import (
    BaseAppException,
    ConfigurationError,
    DeploymentError,
    LogsServiceError,
    ScalingoAPIError,
    ValidationError,
)
from app.core.logging import StructuredLogger, request_context, get_request_context
from app.domain import DomainValidationError, ErrorCode, ErrorContext, FailureReason, OperationExecutionError

logger = StructuredLogger("error_middleware")


def _generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return str(uuid.uuid4())[:8]


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    if request.client:
        return request.client.host
    # Check for forwarded headers
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return None


def _create_error_response(
    error: str,
    message: str,
    status_code: int = 500,
    error_id: Optional[str] = None,
    code: Optional[str] = None,
    timestamp: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Create a standardized error response dictionary."""
    response = {
        "error": error,
        "message": message,
        "status_code": status_code,
    }
    
    if error_id:
        response["error_id"] = error_id
    if code:
        response["code"] = code
    if timestamp:
        response["timestamp"] = timestamp
    
    # Add any extra fields
    response.update(extra)
    
    return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate a request ID for tracking
        request_id = _generate_request_id()
        client_ip = _get_client_ip(request)
        
        # Set up request context for logging
        with request_context(request_id=request_id, client_ip=client_ip):
            try:
                response = await call_next(request)
                return response
            except HTTPException as e:
                # FastAPI HTTP exceptions are already properly formatted
                # But we still want to log them
                logger.warning(
                    "HTTP exception occurred",
                    url=str(request.url),
                    status_code=e.status_code,
                    detail=e.detail,
                    request_id=request_id,
                    client_ip=client_ip,
                )
                raise
            except OperationExecutionError as e:
                error = e.error
                status_code = error.status_code or 500
                
                # Map failure reason to HTTP status code
                if error.reason == FailureReason.VALIDATION:
                    status_code = 400
                elif error.reason == FailureReason.AUTH:
                    status_code = 401
                elif error.reason == FailureReason.NOT_FOUND:
                    status_code = 404
                elif error.reason == FailureReason.CONFLICT:
                    status_code = 409
                elif error.reason == FailureReason.TRANSIENT:
                    status_code = 503

                timestamp = datetime.now(timezone.utc).isoformat()
                error_response = _create_error_response(
                    error="OperationExecutionError",
                    message=error.message,
                    status_code=status_code,
                    error_id=str(error.context.error_id) if error.context else None,
                    code=error.code.value if error.code else None,
                    timestamp=timestamp,
                    reason=error.reason.value,
                    details=error.details,
                )
                
                logger.error(
                    "Operation execution error",
                    url=str(request.url),
                    request_id=request_id,
                    client_ip=client_ip,
                    reason=error.reason.value,
                    status_code=status_code,
                    error_id=str(error.context.error_id) if error.context else None,
                    details=error.details,
                )
                return JSONResponse(
                    status_code=status_code,
                    content=error_response,
                )
            except DomainValidationError as e:
                timestamp = datetime.now(timezone.utc).isoformat()
                error_response = _create_error_response(
                    error="DomainValidationError",
                    message=str(e),
                    status_code=400,
                    error_id=str(e.code.value) if hasattr(e, 'code') else None,
                    timestamp=timestamp,
                    field=e.field if hasattr(e, 'field') else None,
                    value=str(e.value) if hasattr(e, 'value') else None,
                )
                
                logger.error(
                    "Domain validation error",
                    url=str(request.url),
                    request_id=request_id,
                    client_ip=client_ip,
                    message=str(e),
                    field=e.field if hasattr(e, 'field') else None,
                )
                return JSONResponse(
                    status_code=400,
                    content=error_response,
                )
            except BaseAppException as e:
                # Handle all application exceptions consistently
                timestamp = datetime.now(timezone.utc).isoformat()
                error_dict = e.to_dict()
                error_dict.update({
                    "status_code": 500,  # Default, may be overridden
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "timestamp": timestamp,
                })
                
                # Set appropriate status code based on error code
                if e.code == ErrorCode.VALIDATION_ERROR:
                    status_code = 400
                elif e.code == ErrorCode.AUTH_ERROR:
                    status_code = 401
                elif e.code == ErrorCode.RESOURCE_NOT_FOUND:
                    status_code = 404
                elif e.code == ErrorCode.RESOURCE_CONFLICT:
                    status_code = 409
                elif e.code == ErrorCode.TRANSIENT_ERROR:
                    status_code = 503
                else:
                    status_code = 500
                
                error_dict["status_code"] = status_code
                
                logger.error(
                    f"{e.__class__.__name__} occurred",
                    url=str(request.url),
                    request_id=request_id,
                    client_ip=client_ip,
                    error_code=e.code.value,
                    message=e.message,
                    details=e.details,
                )
                return JSONResponse(
                    status_code=status_code,
                    content=error_dict,
                )
            except Exception as e:
                timestamp = datetime.now(timezone.utc).isoformat()
                error_id = str(uuid.uuid4())
                
                # In debug mode, include more details
                show_details = logger.logger.level <= 10  # DEBUG level or lower
                
                error_response = _create_error_response(
                    error="InternalServerError",
                    message="An internal server error occurred",
                    status_code=500,
                    error_id=error_id,
                    code=ErrorCode.UNEXPECTED_ERROR.value,
                    timestamp=timestamp,
                    details=str(e) if show_details else "Details hidden in production",
                )
                
                logger.error(
                    "Unexpected error occurred",
                    url=str(request.url),
                    request_id=request_id,
                    client_ip=client_ip,
                    error_id=error_id,
                    error=str(e),
                    traceback=traceback.format_exc() if show_details else None,
                )
                return JSONResponse(
                    status_code=500,
                    content=error_response,
                )
