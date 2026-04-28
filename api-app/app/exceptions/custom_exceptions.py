"""
Exceptions personnalisées pour l'application.
"""
from typing import Optional, Dict, Any


class BaseAppException(Exception):
    """Exception de base pour l'application."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ScalingoAPIError(BaseAppException):
    """Erreur liée à l'API Scalingo."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        super().__init__(message, details)


class LogsServiceError(BaseAppException):
    """Erreur liée au service de logs."""
    
    def __init__(self, message: str, app_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.app_name = app_name
        super().__init__(message, details)


class DeploymentError(BaseAppException):
    """Erreur liée au déploiement."""
    
    def __init__(self, message: str, app_name: Optional[str] = None, deployment_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.app_name = app_name
        self.deployment_id = deployment_id
        super().__init__(message, details)


class ConfigurationError(BaseAppException):
    """Erreur de configuration."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        self.config_key = config_key
        super().__init__(message)


class ValidationError(BaseAppException):
    """Erreur de validation des données."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.field = field
        self.value = value
        super().__init__(message)
