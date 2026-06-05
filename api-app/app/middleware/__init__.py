"""
Middlewares for the FastAPI application.
"""

from .error_handler import ErrorHandlerMiddleware
from .logging_middleware import LoggingMiddleware
from .auth_middleware import AuthMiddleware, APITokenAuthenticator, JWTAuthenticator
from .rate_limit_middleware import RateLimitMiddleware, RateLimitConfig, RateLimitStore
from .security_middleware import (
    SecurityHeadersMiddleware,
    CORSConfig,
    RequestValidationMiddleware,
    create_security_middleware,
    create_cors_middleware,
    create_request_validation_middleware,
)

__all__ = [
    # Error handling
    "ErrorHandlerMiddleware",
    "LoggingMiddleware",
    # Authentication
    "AuthMiddleware",
    "APITokenAuthenticator",
    "JWTAuthenticator",
    # Rate limiting
    "RateLimitMiddleware",
    "RateLimitConfig",
    "RateLimitStore",
    # Security
    "SecurityHeadersMiddleware",
    "CORSConfig",
    "RequestValidationMiddleware",
    "create_security_middleware",
    "create_cors_middleware",
    "create_request_validation_middleware",
]
