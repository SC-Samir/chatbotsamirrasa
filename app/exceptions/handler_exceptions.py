"""
Exceptions spécifiques aux handlers.
"""
from typing import Optional, Dict, Any
from app.exceptions.custom_exceptions import BaseAppException


class HandlerException(BaseAppException):
    """Exception de base pour les handlers."""
    pass


class ValidationException(HandlerException):
    """Exception pour les erreurs de validation."""
    
    def __init__(self, message: str, missing_fields: Optional[list] = None):
        super().__init__(message)
        self.missing_fields = missing_fields or []


class DeploymentException(HandlerException):
    """Exception pour les erreurs de déploiement."""
    
    def __init__(self, message: str, app_name: str, region: str, deployment_id: Optional[str] = None):
        super().__init__(message)
        self.app_name = app_name
        self.region = region
        self.deployment_id = deployment_id


class ScalingException(HandlerException):
    """Exception pour les erreurs de scaling."""
    
    def __init__(self, message: str, app_name: str, region: str, container_name: str, 
                 target_amount: int, error_type: Optional[str] = None):
        super().__init__(message)
        self.app_name = app_name
        self.region = region
        self.container_name = container_name
        self.target_amount = target_amount
        self.error_type = error_type


class AppManagementException(HandlerException):
    """Exception pour les erreurs de gestion d'application."""
    
    def __init__(self, message: str, app_name: str, region: str, operation: str):
        super().__init__(message)
        self.app_name = app_name
        self.region = region
        self.operation = operation
