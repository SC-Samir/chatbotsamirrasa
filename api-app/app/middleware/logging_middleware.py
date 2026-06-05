"""
Middleware for logging HTTP requests.

This middleware logs all incoming HTTP requests and their responses,
including processing time and status codes.
"""
import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import StructuredLogger, request_context

logger = StructuredLogger("request_middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests."""
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        if request.client:
            return request.client.host
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return None
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Log the incoming request
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=client_ip,
        )
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log the response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s",
            client_ip=client_ip,
        )
        
        return response
