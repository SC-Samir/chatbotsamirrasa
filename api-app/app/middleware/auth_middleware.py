"""
Authentication middleware for API key and JWT authentication.

This middleware provides authentication for HTTP endpoints using
API keys or JWT tokens.
"""
import time
from typing import Any, Callable, Optional, Tuple

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

from app.config import settings
from app.core.logging import StructuredLogger
from app.domain import ErrorCode

logger = StructuredLogger("auth_middleware")


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        detail: str = "Authentication failed",
        headers: Optional[dict] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class APITokenAuthenticator:
    """
    API Key authenticator.
    
    Validates API keys against configured valid keys.
    """
    
    def __init__(self, valid_api_keys: Optional[set] = None):
        self.valid_api_keys = valid_api_keys or self._get_valid_api_keys()
    
    def _get_valid_api_keys(self) -> set:
        """Get valid API keys from configuration."""
        # Check if API keys are configured in settings
        api_keys = getattr(settings, 'api_keys', None)
        if api_keys:
            if isinstance(api_keys, str):
                return {api_keys}
            elif isinstance(api_keys, list):
                return set(api_keys)
        return set()
    
    def validate(self, api_key: str) -> bool:
        """Validate an API key."""
        if not api_key:
            return False
        return api_key in self.valid_api_keys


class JWTAuthenticator:
    """
    JWT token authenticator.
    
    Validates JWT tokens (stub implementation - actual JWT validation
    would require additional libraries like PyJWT).
    """
    
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or getattr(settings, 'jwt_secret_key', 'secret')
        self.algorithm = algorithm
        self._enabled = bool(self.secret_key and self.secret_key != 'secret')
    
    @property
    def enabled(self) -> bool:
        """Check if JWT authentication is enabled."""
        return self._enabled
    
    def validate(self, token: str) -> bool:
        """Validate a JWT token."""
        if not self._enabled:
            return False
        
        if not token:
            return False
        
        # Stub: In a real implementation, we would decode and verify the token
        # For now, just check if it's a non-empty string
        try:
            import jwt
            # Try to decode without verification for basic validation
            payload = jwt.decode(token, options={"verify_signature": False})
            return True
        except ImportError:
            logger.warning("PyJWT not installed, JWT validation disabled")
            return False
        except Exception:
            return False
    
    def decode(self, token: str) -> Optional[dict]:
        """Decode a JWT token and return payload."""
        if not self._enabled:
            return None
        
        try:
            import jwt
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except Exception as e:
            logger.warning(f"JWT decode failed: {e}")
            return None


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for FastAPI.
    
    This middleware authenticates requests using API keys or JWT tokens.
    It supports multiple authentication methods:
    - API key in X-API-Key header
    - API key in Authorization header (Bearer)
    - API key as query parameter
    - JWT token in Authorization header (Bearer)
    """
    
    def __init__(
        self,
        app,
        require_auth: bool = False,
        exclude_paths: Optional[list] = None,
        api_key_authenticator: Optional[APITokenAuthenticator] = None,
        jwt_authenticator: Optional[JWTAuthenticator] = None,
    ):
        super().__init__(app)
        self.require_auth = require_auth
        self.exclude_paths = exclude_paths or [
            "/health",
            "/health/",
            "/health/ready",
            "/health/live",
            "/health/metrics",
            "/health/info",
            "/health/dependencies",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/",
            "/static",
            "/ws",
            "/ws/",
        ]
        self.api_key_auth = api_key_authenticator or APITokenAuthenticator()
        self.jwt_auth = jwt_authenticator or JWTAuthenticator()
    
    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from authentication."""
        for exclude_path in self.exclude_paths:
            if path == exclude_path or path.startswith(exclude_path + "/"):
                return True
            if exclude_path.endswith("/") and path.startswith(exclude_path):
                return True
        return False
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from various sources."""
        # Check X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:].strip()
                # Could be API key or JWT token
                return token
            elif auth_header.lower().startswith("api-key "):
                return auth_header[8:].strip()
        
        # Check query parameters
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key
        
        # Check query parameters (alternative names)
        api_key = request.query_params.get("apikey")
        if api_key:
            return api_key
        
        return None
    
    def _authenticate(self, request: Request) -> Tuple[bool, Optional[dict]]:
        """
        Authenticate the request.
        
        Returns:
            Tuple of (is_authenticated, user_info)
        """
        # Extract API key
        api_key = self._extract_api_key(request)
        
        if api_key and self.api_key_auth.validate(api_key):
            return True, {"auth_type": "api_key", "authenticated": True}
        
        # Try JWT authentication
        if self.jwt_auth.enabled:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                token = auth_header[7:].strip()
                if self.jwt_auth.validate(token):
                    payload = self.jwt_auth.decode(token)
                    return True, {
                        "auth_type": "jwt",
                        "authenticated": True,
                        "user": payload,
                    }
        
        return False, None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Dispatch request with authentication."""
        path = request.url.path
        
        # Skip authentication for excluded paths
        if self._should_exclude(path):
            return await call_next(request)
        
        # Skip authentication if not required
        if not self.require_auth:
            return await call_next(request)
        
        # Authenticate
        is_authenticated, user_info = self._authenticate(request)
        
        if not is_authenticated:
            logger.warning(
                "Authentication failed",
                path=path,
                method=request.method,
                client_ip=request.client.host if request.client else None,
            )
            raise AuthenticationError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide a valid API key or JWT token.",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Add user info to request state
        request.state.user_info = user_info or {}
        request.state.authenticated = True
        
        # Add authentication context to logging
        logger.info(
            "Request authenticated",
            path=path,
            method=request.method,
            auth_type=user_info.get("auth_type") if user_info else None,
        )
        
        # Process the request
        response = await call_next(request)
        
        return response


def create_auth_middleware(
    require_auth: bool = False,
    exclude_paths: Optional[list] = None,
) -> AuthMiddleware:
    """
    Factory function to create authentication middleware.
    
    Args:
        require_auth: Whether authentication is required
        exclude_paths: Paths to exclude from authentication
        
    Returns:
        AuthMiddleware instance
    """
    return AuthMiddleware(
        app=None,  # Will be set by FastAPI
        require_auth=require_auth,
        exclude_paths=exclude_paths,
    )
