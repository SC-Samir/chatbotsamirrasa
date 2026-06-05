"""
Cache middleware for FastAPI.

This middleware provides:
- Response caching
- Cache invalidation based on paths/tags
- Cache control headers
- Conditional requests (ETag, Last-Modified)
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import StructuredLogger
from app.infrastructure.cache import get_cache_manager, CacheManager

logger = StructuredLogger("cache_middleware")


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for caching HTTP responses.
    
    Supports:
    - Response caching with configurable TTL
    - Path-based cache invalidation
    - Tag-based cache invalidation
    - Cache control headers
    - ETag and Last-Modified support
    """
    
    def __init__(
        self,
        app,
        cache_manager: Optional[CacheManager] = None,
        default_ttl: int = 300,
        cacheable_methods: Set[str] = {"GET", "HEAD"},
        cacheable_paths: Optional[Set[str]] = None,
        non_cacheable_paths: Optional[Set[str]] = None,
        etag_enabled: bool = True,
        last_modified_enabled: bool = True,
    ):
        super().__init__(app)
        self.cache_manager = cache_manager or get_cache_manager()
        self.default_ttl = default_ttl
        self.cacheable_methods = cacheable_methods
        self.cacheable_paths = cacheable_paths or set()
        self.non_cacheable_paths = non_cacheable_paths or set()
        self.etag_enabled = etag_enabled
        self.last_modified_enabled = last_modified_enabled
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and cache response if applicable."""
        # Skip caching for non-cacheable methods
        if request.method not in self.cacheable_methods:
            response = await call_next(request)
            await self._handle_cache_invalidation(request, response)
            return response
        
        # Check if path is cacheable
        if not self._is_cacheable_path(request.url.path):
            return await call_next(request)
        
        # Check for cache bypass headers
        if self._should_bypass_cache(request):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to serve from cache
        cached_response = self._get_cached_response(request, cache_key)
        if cached_response is not None:
            logger.debug("Cache hit", path=request.url.path, key=cache_key)
            return cached_response
        
        # Call next middleware/endpoint
        response = await call_next(request)
        
        # Cache the response if it's cacheable
        if self._is_cacheable_response(response):
            await self._cache_response(request, response, cache_key)
        
        # Handle cache invalidation
        await self._handle_cache_invalidation(request, response)
        
        return response
    
    def _is_cacheable_path(self, path: str) -> bool:
        """Check if a path is cacheable."""
        # Check non-cacheable paths first
        for non_cacheable in self.non_cacheable_paths:
            if path.startswith(non_cacheable) or path == non_cacheable:
                return False
        
        # If cacheable_paths is defined, only cache those
        if self.cacheable_paths:
            for cacheable in self.cacheable_paths:
                if path.startswith(cacheable) or path == cacheable:
                    return True
            return False
        
        # Default: cache all paths
        return True
    
    def _should_bypass_cache(self, request: Request) -> bool:
        """Check if cache should be bypassed for this request."""
        # Check for Cache-Control: no-cache
        cache_control = getattr(request.headers, "cache-control", "").lower()
        if "no-cache" in cache_control or "no-store" in cache_control:
            return True
        
        # Check for Authorization header (don't cache authenticated requests by default)
        if "authorization" in request.headers:
            return True
        
        # Check for query parameters that bypass cache
        if request.query_params.get("no_cache") or request.query_params.get("nocache"):
            return True
        
        return False
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate a unique cache key for the request."""
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]
        
        # Include relevant headers in cache key
        for header in ["accept", "accept-language", "accept-encoding"]:
            if header in request.headers:
                key_parts.append(f"{header}={request.headers[header]}")
        
        key_string = "|".join(key_parts)
        return f"http:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _get_cached_response(self, request: Request, cache_key: str) -> Optional[Response]:
        """Get a cached response if it exists and is valid."""
        cached_data, hit = self.cache_manager.get(cache_key)
        if not hit or cached_data is None:
            return None
        
        try:
            # Parse cached data
            response_data = json.loads(cached_data)
            
            # Check ETag if enabled
            if self.etag_enabled and "etag" in request.headers:
                client_etag = request.headers["etag"].strip('"')
                server_etag = response_data.get("etag", "")
                if client_etag == server_etag:
                    return Response(status_code=304, headers={"ETag": f'"{server_etag}"'})
            
            # Check If-Modified-Since if enabled
            if self.last_modified_enabled and "if-modified-since" in request.headers:
                last_modified = response_data.get("last_modified", "")
                if last_modified:
                    try:
                        last_modified_time = time.mktime(time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT"))
                        if_modified_since = time.mktime(time.strptime(
                            request.headers["if-modified-since"],
                            "%a, %d %b %Y %H:%M:%S GMT"
                        ))
                        if last_modified_time <= if_modified_since:
                            return Response(status_code=304)
                    except (ValueError, KeyError):
                        pass
            
            # Reconstruct response
            return JSONResponse(
                content=response_data.get("body", {}),
                status_code=response_data.get("status_code", 200),
                headers=response_data.get("headers", {}),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse cached response", key=cache_key, error=str(e))
            return None
    
    def _is_cacheable_response(self, response: Response) -> bool:
        """Check if a response is cacheable."""
        # Don't cache error responses (4xx, 5xx)
        if 400 <= response.status_code < 600:
            return False
        
        # Check for explicit no-cache headers
        cache_control = getattr(response.headers, "cache-control", "").lower()
        if "no-cache" in cache_control or "no-store" in cache_control or "private" in cache_control:
            return False
        
        # Check if response is JSON (easier to cache)
        content_type = getattr(response.headers, "content-type", "").lower()
        if "application/json" not in content_type:
            return False
        
        return True
    
    async def _cache_response(self, request: Request, response: Response, cache_key: str) -> None:
        """Cache a response."""
        try:
            # Get TTL from headers or use default
            cache_control = getattr(response.headers, "cache-control", "").lower()
            ttl = self.default_ttl
            
            if "max-age=" in cache_control:
                max_age_part = cache_control.split("max-age=")[1].split(",")[0]
                try:
                    ttl = int(max_age_part)
                except ValueError:
                    pass
            
            # Prepare response data
            response_data = {
                "status_code": response.status_code,
                "body": response.body,
                "headers": dict(response.headers),
            }
            
            # Add ETag if enabled
            if self.etag_enabled:
                body_hash = hashlib.md5(response.body).hexdigest()
                response_data["etag"] = body_hash
            
            # Add Last-Modified if enabled
            if self.last_modified_enabled:
                response_data["last_modified"] = time.strftime(
                    "%a, %d %b %Y %H:%M:%S GMT",
                    time.gmtime()
                )
            
            # Cache the response
            self.cache_manager.set(
                key=cache_key,
                value=json.dumps(response_data),
                ttl=ttl,
                tags=[f"path:{request.url.path}", f"method:{request.method}"],
            )
            
            logger.debug("Response cached", path=request.url.path, key=cache_key, ttl=ttl)
        except Exception as e:
            logger.error("Failed to cache response", path=request.url.path, error=str(e))
    
    async def _handle_cache_invalidation(self, request: Request, response: Response) -> None:
        """Handle cache invalidation based on response."""
        # Invalidate cache for POST, PUT, PATCH, DELETE requests
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Invalidate cache for the same path
            path_tag = f"path:{request.url.path}"
            self.cache_manager.invalidate_by_tag(path_tag)
            
            # Also invalidate for the parent path
            parent_path = request.url.path.rsplit("/", 1)[0]
            if parent_path:
                parent_tag = f"path:{parent_path}"
                self.cache_manager.invalidate_by_tag(parent_tag)
            
            logger.debug("Cache invalidated", method=request.method, path=request.url.path)
        
        # Check for explicit cache invalidation headers
        if "x-cache-invalidate" in response.headers:
            paths_to_invalidate = response.headers["x-cache-invalidate"].split(",")
            for path in paths_to_invalidate:
                self.cache_manager.invalidate_by_tag(f"path:{path.strip()}")


class CacheControlMiddleware:
    """
    Middleware to add cache control headers to responses.
    """
    
    def __init__(self, app, default_cache_control: str = "public, max-age=300"):
        self.app = app
        self.default_cache_control = default_cache_control
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Add cache control header if not already present
                if "cache-control" not in headers:
                    headers[b"cache-control"] = self.default_cache_control.encode()
                
                # Add ETag header if response has body
                if "body" in message and message["body"]:
                    body = message["body"]
                    if isinstance(body, bytes):
                        etag = hashlib.md5(body).hexdigest()
                    else:
                        etag = hashlib.md5(str(body).encode()).hexdigest()
                    headers[b"etag"] = f'"{etag}"'.encode()
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


# Helper functions for cache management

def cache_by_user(user_id: str, prefix: str = "") -> str:
    """Generate a user-specific cache key."""
    return f"user:{user_id}:{prefix}"


def cache_by_app(app_id: str, region: str, prefix: str = "") -> str:
    """Generate an app-specific cache key."""
    return f"app:{app_id}:{region}:{prefix}"


def cache_by_path(path: str, **kwargs) -> str:
    """Generate a path-based cache key with query parameters."""
    key_parts = [path]
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}={value}")
    return f"path:{''.join(key_parts)}"


# Decorator for caching endpoint responses

def cached_endpoint(
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None,
    key_func: Optional[Callable[..., str]] = None,
):
    """
    Decorator to cache endpoint responses.
    
    Args:
        ttl: Time to live in seconds
        tags: List of tags for cache invalidation
        key_func: Function to generate cache key
    
    Returns:
        Decorator function
    """
    def decorator(func):
        cache_manager = get_cache_manager()
        
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key based on function name and arguments
                key_parts = [func.__name__]
                for arg in args:
                    key_parts.append(str(arg))
                for key, value in sorted(kwargs.items()):
                    key_parts.append(f"{key}={value}")
                cache_key = f"endpoint:{hashlib.md5('|'.join(key_parts).encode()).hexdigest()}"
            
            # Try to get from cache
            cached_data, hit = cache_manager.get(cache_key)
            if hit:
                logger.debug("Endpoint cache hit", func=func.__name__, key=cache_key)
                return JSONResponse(content=cached_data, status_code=200)
            
            # Call the endpoint
            response = await func(*args, **kwargs)
            
            # Cache the response
            if response.status_code == 200:
                try:
                    response_data = json.loads(response.body)
                    cache_manager.set(
                        key=cache_key,
                        value=response_data,
                        ttl=ttl,
                        tags=tags,
                    )
                    logger.debug("Endpoint cached", func=func.__name__, key=cache_key)
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            return response
        
        return wrapper
    
    return decorator
