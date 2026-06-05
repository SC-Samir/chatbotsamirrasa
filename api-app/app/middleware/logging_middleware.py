"""
Middleware for request/response logging.

This middleware provides comprehensive logging for all HTTP requests,
including request details, timing information, and response metrics.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import StructuredLogger, request_context

logger = StructuredLogger("access_log")


def _generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return str(uuid.uuid4())


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    if request.client:
        return request.client.host
    # Check for forwarded headers
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return None


def _sanitize_url(url: str) -> str:
    """Sanitize URL for logging by removing sensitive parameters."""
    if not url:
        return url
    
    # Remove query parameters that might contain sensitive data
    sensitive_params = ["token", "password", "secret", "api_key", "access_token"]
    
    try:
        from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Filter out sensitive parameters
        filtered_params = {}
        for key, values in query_params.items():
            if not any(sensitive in key.lower() for sensitive in sensitive_params):
                filtered_params[key] = values
        
        # Rebuild URL with filtered parameters
        filtered_query = urlencode(filtered_params, doseq=True)
        sanitized_parts = (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            filtered_query,
            parsed.fragment,
        )
        return urlunparse(sanitized_parts)
    except Exception:
        # If parsing fails, return the original URL
        return url


def _get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("user-agent")


def _get_content_length(request: Request) -> Optional[int]:
    """Extract content length from request."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            return int(content_length)
        except ValueError:
            return None
    return None


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.
    
    This middleware:
    - Logs all incoming requests with detailed information
    - Measures request processing time
    - Logs response status codes and sizes
    - Handles request context for correlation across logs
    - Sanitizes sensitive data from logs
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID for correlation
        request_id = _generate_request_id()
        client_ip = _get_client_ip(request)
        user_agent = _get_user_agent(request)
        
        # Extract request information
        method = request.method
        url = str(request.url)
        sanitized_url = _sanitize_url(url)
        path = request.url.path
        
        # Get request headers for logging (sanitized)
        headers = dict(request.headers)
        # Remove potentially sensitive headers
        sensitive_headers = ["authorization", "cookie", "set-cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"
        
        # Set up request context for structured logging
        with request_context(
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            method=method,
            path=path,
        ):
            # Log the incoming request
            logger.info(
                "Request started",
                request_id=request_id,
                method=method,
                path=path,
                url=sanitized_url,
                client_ip=client_ip,
                user_agent=user_agent,
                content_length=_get_content_length(request),
                headers=headers,
            )
            
            # Record start time
            start_time = time.time()
            
            try:
                # Process the request
                response = await call_next(request)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                processing_time_ms = processing_time * 1000
                
                # Get response information
                status_code = response.status_code
                
                # Determine response category
                if 200 <= status_code < 300:
                    status_category = "success"
                elif 300 <= status_code < 400:
                    status_category = "redirect"
                elif 400 <= status_code < 500:
                    status_category = "client_error"
                else:
                    status_category = "server_error"
                
                # Get response size
                response_size = 0
                if hasattr(response, "body") and response.body:
                    response_size = len(response.body)
                elif hasattr(response, "content") and response.content:
                    response_size = len(response.content)
                
                # Log the completed request
                logger.info(
                    "Request completed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    status_category=status_category,
                    processing_time_ms=round(processing_time_ms, 2),
                    response_size=response_size,
                    client_ip=client_ip,
                )
                
                # Add request ID to response headers for client correlation
                if not hasattr(response, "headers") or response.headers is None:
                    response.headers = {}
                response.headers["X-Request-ID"] = request_id
                
                return response
                
            except Exception as e:
                # Calculate processing time even for errors
                processing_time = time.time() - start_time
                processing_time_ms = processing_time * 1000
                
                # Log the error
                logger.error(
                    "Request failed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    processing_time_ms=round(processing_time_ms, 2),
                    error=str(e),
                    client_ip=client_ip,
                )
                
                # Re-raise the exception for the error handler middleware
                raise
