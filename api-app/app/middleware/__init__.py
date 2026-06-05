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
from .cache_middleware import (
    CacheMiddleware,
    CacheControlMiddleware,
    cached_endpoint,
    cache_by_user,
    cache_by_app,
    cache_by_path,
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
    # Caching
    "CacheMiddleware",
    "CacheControlMiddleware",
    "cached_endpoint",
    "cache_by_user",
    "cache_by_app",
    "cache_by_path",
]
