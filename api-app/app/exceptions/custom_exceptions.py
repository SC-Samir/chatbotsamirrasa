"""
Custom application exceptions.

This module provides application-specific exception types that extend
or complement the domain layer error types.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.domain.errors import ErrorCode, ErrorContext, FailureReason


class BaseAppException(Exception):
    """
    Base exception for the application.
    
    All custom application exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.context = context
        self.timestamp = datetime.now(timezone.utc)
        self.error_id = uuid4()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "error_id": str(self.error_id),
            "code": self.code.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            **self.details,
        }


class ScalingoAPIError(BaseAppException):
    """Error related to the Scalingo API."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.status_code = status_code
        super().__init__(message, ErrorCode.UPSTREAM_ERROR, details, context)


class LogsServiceError(BaseAppException):
    """Error related to the logs service."""
    
    def __init__(
        self,
        message: str,
        app_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.app_name = app_name
        super().__init__(message, ErrorCode.SERVICE_UNAVAILABLE, details, context)


class DeploymentError(BaseAppException):
    """Error related to deployment operations."""
    
    def __init__(
        self,
        message: str,
        app_name: Optional[str] = None,
        deployment_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.app_name = app_name
        self.deployment_id = deployment_id
        super().__init__(message, ErrorCode.TRANSIENT_ERROR, details, context)


class ConfigurationError(BaseAppException):
    """Error related to application configuration."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.config_key = config_key
        super().__init__(message, ErrorCode.CONFIGURATION_ERROR, details, context)


class ValidationError(BaseAppException):
    """Error related to data validation."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.field = field
        self.value = value
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details, context)
        
        # Add field and value to details for backward compatibility
        if self.field:
            self.details["field"] = self.field
        if self.value is not None:
            self.details["value"] = str(self.value)
