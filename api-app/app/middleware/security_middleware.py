"""
Security middleware for FastAPI.

This middleware implements security headers and CORS configuration.
"""
from typing import Any, Callable, List, Optional, Set

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.config import settings
from app.core.logging import StructuredLogger

logger = StructuredLogger("security_middleware")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    
    Adds standard security headers to all responses:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(
        self,
        app,
        content_security_policy: Optional[str] = None,
        force_https: bool = False,
        frame_options: str = "DENY",
        xss_protection: str = "1; mode=block",
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[str] = None,
    ):
        super().__init__(app)
        self.content_security_policy = content_security_policy or self._default_csp()
        self.force_https = force_https
        self.frame_options = frame_options
        self.xss_protection = xss_protection
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy or self._default_permissions()
    
    def _default_csp(self) -> str:
        """Get default Content-Security-Policy header value."""
        # Default CSP that works with FastAPI docs and common use cases
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
        return "; ".join(directives)
    
    def _default_permissions(self) -> str:
        """Get default Permissions-Policy header value."""
        permissions = [
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()",
        ]
        return ", ".join(permissions)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["Content-Security-Policy"] = self.content_security_policy
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = self.frame_options
        response.headers["X-XSS-Protection"] = self.xss_protection
        response.headers["Referrer-Policy"] = self.referrer_policy
        response.headers["Permissions-Policy"] = self.permissions_policy
        
        # Add HSTS header if HTTPS
        if self.force_https or request.url.scheme == "https":
            hsts_directives = [f"max-age={self.hsts_max_age}"]
            if self.hsts_include_subdomains:
                hsts_directives.append("includeSubDomains")
            if self.hsts_preload:
                hsts_directives.append("preload")
            response.headers["Strict-Transport-Security"] = "; ".join(hsts_directives)
        
        # Add request ID if not already present
        if "X-Request-ID" not in response.headers:
            import uuid
            response.headers["X-Request-ID"] = str(uuid.uuid4())
        
        return response


class CORSConfig:
    """Configuration for CORS middleware."""
    
    def __init__(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_origin_regex: Optional[str] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 600,
    ):
        # Default to allowing all origins if not specified
        self.allow_origins = allow_origins or ["*"]
        self.allow_origin_regex = allow_origin_regex
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ]
        self.max_age = max_age
    
    @classmethod
    def from_settings(cls) -> "CORSConfig":
        """Create CORS configuration from settings."""
        allow_origins = getattr(settings, 'cors_origins', None)
        if allow_origins:
            if isinstance(allow_origins, str):
                allow_origins = [allow_origins]
        
        return cls(
            allow_origins=allow_origins,
            allow_credentials=getattr(settings, 'cors_allow_credentials', True),
            allow_methods=getattr(settings, 'cors_allow_methods', None),
            allow_headers=getattr(settings, 'cors_allow_headers', None),
            expose_headers=getattr(settings, 'cors_expose_headers', None),
            max_age=getattr(settings, 'cors_max_age', 600),
        )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating incoming requests.
    
    Performs validation on:
    - Content-Type headers
    - Request body size
    - Required headers
    - Request structure
    """
    
    def __init__(
        self,
        app,
        max_content_length: int = 10 * 1024 * 1024,  # 10MB
        allowed_content_types: Optional[List[str]] = None,
        required_headers: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.max_content_length = max_content_length
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]
        self.required_headers = required_headers or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request and process."""
        # Check content length
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                content_length_int = int(content_length)
                if content_length_int > self.max_content_length:
                    logger.warning(
                        "Request too large",
                        path=request.url.path,
                        content_length=content_length_int,
                        max_allowed=self.max_content_length,
                    )
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                        detail=f"Request body too large. Maximum allowed: {self.max_content_length} bytes",
                    )
            except ValueError:
                pass
        
        # Check content type for non-GET requests
        if request.method not in ["GET", "HEAD", "OPTIONS"]:
            content_type = request.headers.get("Content-Type", "")
            if content_type and not any(
                content_type.startswith(allowed) 
                for allowed in self.allowed_content_types
            ):
                logger.warning(
                    "Invalid content type",
                    path=request.url.path,
                    content_type=content_type,
                )
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported content type: {content_type}",
                )
        
        # Check required headers
        for header in self.required_headers:
            if header not in request.headers:
                logger.warning(
                    "Missing required header",
                    path=request.url.path,
                    header=header,
                )
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required header: {header}",
                )
        
        # Process request
        response = await call_next(request)
        return response


def create_security_middleware(
    content_security_policy: Optional[str] = None,
    force_https: bool = False,
) -> SecurityHeadersMiddleware:
    """
    Factory function to create security headers middleware.
    
    Args:
        content_security_policy: Custom CSP header value
        force_https: Whether to force HTTPS
        
    Returns:
        SecurityHeadersMiddleware instance
    """
    return SecurityHeadersMiddleware(
        app=None,
        content_security_policy=content_security_policy,
        force_https=force_https,
    )


def create_cors_middleware(config: Optional[CORSConfig] = None) -> CORSMiddleware:
    """
    Factory function to create CORS middleware.
    
    Args:
        config: CORS configuration (uses settings if not provided)
        
    Returns:
        CORSMiddleware instance
    """
    if config is None:
        config = CORSConfig.from_settings()
    
    return CORSMiddleware(
        app=None,
        allow_origins=config.allow_origins,
        allow_origin_regex=config.allow_origin_regex,
        allow_methods=config.allow_methods,
        allow_headers=config.allow_headers,
        allow_credentials=config.allow_credentials,
        expose_headers=config.expose_headers,
        max_age=config.max_age,
    )


def create_request_validation_middleware(
    max_content_length: int = 10 * 1024 * 1024,
    allowed_content_types: Optional[List[str]] = None,
    required_headers: Optional[List[str]] = None,
) -> RequestValidationMiddleware:
    """
    Factory function to create request validation middleware.
    
    Args:
        max_content_length: Maximum allowed content length
        allowed_content_types: Allowed content types
        required_headers: Required headers for all requests
        
    Returns:
        RequestValidationMiddleware instance
    """
    return RequestValidationMiddleware(
        app=None,
        max_content_length=max_content_length,
        allowed_content_types=allowed_content_types,
        required_headers=required_headers,
    )
