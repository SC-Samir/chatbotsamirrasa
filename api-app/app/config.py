"""
Configuration centralisée pour l'application.
"""
from typing import Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    # Scalingo API
    scalingo_api_token: str = Field(..., description="Scalingo API token (required)")
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

    @field_validator('scalingo_api_token')
    @classmethod
    def validate_api_token(cls, v):
        if not v:
            raise ValueError("SCALINGO_API_TOKEN est requis")
        return v

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


# Instance globale des settings
settings = Settings()
