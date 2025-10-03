"""
Configuration centralisée pour l'application.
"""
import os
from typing import Dict, Any
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    # Scalingo API
    scalingo_api_token: str
    scalingo_region_urls: Dict[str, str] = {
        "osc-fr1": "https://api.osc-fr1.scalingo.com",
        "osc-secnum-fr1": "https://api.osc-secnum-fr1.scalingo.com"
    }
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Rasa
    rasa_model_path: str = "models/nlu-20251003-132153-soft-cleat.tar.gz"
    
    # Application
    app_name: str = "ScalingoOps Agent"
    debug: bool = False
    
    # Logs
    default_log_lines: int = 100
    log_chunk_size: int = 10
    log_status_interval: int = 50
    
    # Deployment
    deployment_poll_interval: int = 10
    
    @validator('scalingo_api_token')
    def validate_api_token(cls, v):
        if not v:
            raise ValueError("SCALINGO_API_TOKEN est requis")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instance globale des settings
settings = Settings()
