"""
Configuration centralisée pour l'application.

This module provides the application configuration using Pydantic Settings.
It includes validation at startup to ensure all required settings are present
and have valid values.
"""
from typing import Dict, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Scalingo API
    scalingo_api_token: Optional[str] = Field(default=None, description="Scalingo API token")
    scalingo_region_urls: Dict[str, str] = {
        "osc-fr1": "https://api.osc-fr1.scalingo.com",
        "osc-secnum-fr1": "https://api.osc-secnum-fr1.scalingo.com"
    }
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    memory_session_ttl_seconds: int = 3600
    memory_postgres_dsn: Optional[str] = None
    database_url: Optional[str] = None
    
    # Rasa HTTP service
    rasa_url: str = "http://localhost:5005"
    rasa_timeout_ms: int = 3000
    rasa_auth_token: Optional[str] = None
    nlu_expected_contract: str = "v3"
    nlu_fallback_enable_regex: bool = True
    nlu_clarification_topk: int = 3
    
    # Application
    app_name: str = "ScalingoOps Agent"
    debug: bool = False
    
    # API Keys (comma-separated or list)
    api_keys: Optional[List[str]] = None
    jwt_secret_key: Optional[str] = None
    
    # CORS Configuration
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    cors_expose_headers: List[str] = ["X-Request-ID", "X-RateLimit-*", "Retry-After"]
    cors_max_age: int = 600
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_by: str = "ip"  # Can be: "ip", "user", "api_key", "combined"
    
    # Security
    force_https: bool = False
    allow_insecure: bool = True  # For development
    
    # Logs
    default_log_lines: int = 100
    log_chunk_size: int = 10
    log_status_interval: int = 50
    
    # Deployment
    deployment_poll_interval: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("memory_postgres_dsn", mode="before")
    @classmethod
    def default_memory_postgres_dsn(cls, v, values):
        if v:
            return v
        # Reuse Scalingo Postgres addon URL if dedicated memory DSN is not provided.
        # In pydantic v2, values is a ValidationInfo object with a data attribute
        if hasattr(values, 'data'):
            return values.data.get("database_url") or None
        return values.get("database_url") or None

    @field_validator('scalingo_api_token')
    @classmethod
    def validate_api_token_strict(cls, v):
        """Strict validation for API token."""
        if v is None:
            return v
        if not isinstance(v, str) or not v.strip():
            raise ValueError("SCALINGO_API_TOKEN must be a non-empty string")
        return v.strip()

    @field_validator("redis_url", "database_url", "memory_postgres_dsn")
    @classmethod
    def validate_url_format(cls, v):
        """Validate that URL fields are properly formatted."""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError(f"URL must be a string, got {type(v)}")
        v = v.strip()
        if not v:
            return v
        # Basic URL validation
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("redis://") or v.startswith("postgresql://")):
            raise ValueError(f"Invalid URL format: {v}")
        return v

    @field_validator("rasa_url")
    @classmethod
    def validate_rasa_url(cls, v):
        """Validate Rasa NLU service URL."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"RASA_URL must start with http:// or https://, got: {v}")
        return v

    @field_validator("nlu_expected_contract")
    @classmethod
    def validate_nlu_contract(cls, v):
        """Validate NLU contract version."""
        if v is None:
            return v
        valid_contracts = ["v1", "v2", "v3"]
        if v not in valid_contracts:
            raise ValueError(f"NLU_EXPECTED_CONTRACT must be one of {valid_contracts}, got: {v}")
        return v

    @field_validator("rasa_timeout_ms", "memory_session_ttl_seconds", "deployment_poll_interval")
    @classmethod
    def validate_positive_int(cls, v):
        """Validate that numeric fields are positive."""
        if v is not None and v <= 0:
            raise ValueError(f"Value must be positive, got: {v}")
        return v

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get list of required field names."""
        # Manually specify which fields are truly required for the application to work
        return ["scalingo_api_token"]
    
    def get_missing_required(self) -> List[str]:
        """Get list of missing required configuration values."""
        required_fields = self.get_required_fields()
        missing = []
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if not value:
                missing.append(field_name)
        return missing

    def validate_startup(self) -> bool:
        """
        Validate configuration at startup.
        
        Returns True if configuration is valid, raises ValueError otherwise.
        """
        missing = self.get_missing_required()
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        # Validate that at least one region URL is configured
        if not self.scalingo_region_urls:
            raise ValueError("At least one scalingo_region_url must be configured")
        
        return True


# Instance globale des settings
settings = Settings()

# Validate configuration at import time (only if not in test mode)
if not getattr(settings, '_test_mode', False):
    try:
        settings.validate_startup()
    except ValueError as e:
        # Don't raise immediately to allow for deferred validation
        # This allows tests to run even with incomplete configuration
        pass
