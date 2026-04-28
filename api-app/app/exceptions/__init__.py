"""
Exceptions personnalisées pour l'application.
"""
from .custom_exceptions import (
    ScalingoAPIError,
    LogsServiceError,
    DeploymentError,
    ConfigurationError,
    ValidationError
)

__all__ = [
    "ScalingoAPIError",
    "LogsServiceError", 
    "DeploymentError",
    "ConfigurationError",
    "ValidationError"
]
