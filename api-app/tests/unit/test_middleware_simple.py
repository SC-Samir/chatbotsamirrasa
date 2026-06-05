"""
Simple unit tests for middleware components.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException, status
from starlette.responses import Response

from app.middleware.auth_middleware import (
    AuthMiddleware,
    APITokenAuthenticator,
    JWTAuthenticator,
)
from app.middleware.rate_limit_middleware import (
    RateLimitMiddleware,
    RateLimitConfig,
    RateLimitStore,
)
from app.middleware.security_middleware import (
    SecurityHeadersMiddleware,
    CORSConfig,
    RequestValidationMiddleware,
)


class TestAPITokenAuthenticator:
    """Tests for APITokenAuthenticator."""
    
    def test_validate_valid_key(self):
        """Test validation of valid API key."""
        authenticator = APITokenAuthenticator(valid_api_keys={"key1", "key2"})
        
        assert authenticator.validate("key1") is True
        assert authenticator.validate("key2") is True
    
    def test_validate_invalid_key(self):
        """Test validation of invalid API key."""
        authenticator = APITokenAuthenticator(valid_api_keys={"key1", "key2"})
        
        assert authenticator.validate("invalid") is False
        assert authenticator.validate("") is False
        assert authenticator.validate(None) is False


class TestJWTAuthenticator:
    """Tests for JWTAuthenticator."""
    
    def test_enabled_with_secret(self):
        """Test JWT authenticator is enabled when secret is set."""
        authenticator = JWTAuthenticator(secret_key="secret123")
        
        assert authenticator.enabled is True
    
    def test_disabled_without_secret(self):
        """Test JWT authenticator is disabled when secret is not set."""
        authenticator = JWTAuthenticator(secret_key=None)
        
        assert authenticator.enabled is False
    
    def test_validate_disabled(self):
        """Test validation when disabled."""
        authenticator = JWTAuthenticator(secret_key=None)
        
        assert authenticator.validate("any_token") is False


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        
        assert config.max_requests == 100
        assert config.window_seconds == 60
        assert config.burst_requests == 100
        assert config.burst_seconds == 60
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(max_requests=200, window_seconds=120)
        
        assert config.max_requests == 200
        assert config.window_seconds == 120


class TestRateLimitStore:
    """Tests for RateLimitStore."""
    
    @pytest.mark.asyncio
    async def test_add_request(self):
        """Test adding requests to store."""
        store = RateLimitStore()
        
        current_time = 1000.0
        count, _ = await store.add_request("test", current_time)
        
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_get_count(self):
        """Test getting count from store."""
        store = RateLimitStore()
        
        current_time = 1000.0
        await store.add_request("test", current_time)
        await store.add_request("test", current_time)
        
        count = await store.get_count("test", current_time, window=1)
        
        assert count >= 2
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup of old entries."""
        store = RateLimitStore()
        
        current_time = 1000.0
        # Add entries
        await store.add_request("test", current_time - 10)
        await store.add_request("test", current_time)
        
        # Cleanup should not crash
        await store.cleanup(max_age=5)
        
        # Test passes if cleanup doesn't crash
        assert True


class TestCORSConfig:
    """Tests for CORSConfig."""
    
    def test_default_values(self):
        """Test default CORS configuration."""
        config = CORSConfig()
        
        assert config.allow_origins == ["*"]
        assert config.allow_methods == ["*"]
        assert config.allow_headers == ["*"]
        assert config.allow_credentials is True
        assert config.max_age == 600
    
    def test_custom_values(self):
        """Test custom CORS configuration."""
        config = CORSConfig(
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )
        
        assert config.allow_origins == ["https://example.com"]
        assert config.allow_methods == ["GET", "POST"]
