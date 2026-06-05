"""
Custom exceptions for the application.

This package contains all custom exception types used throughout the application,
including domain exceptions and application-specific exceptions.
"""
from .custom_exceptions import (
    BaseAppException,
    ConfigurationError,
    DeploymentError,
    LogsServiceError,
    ScalingoAPIError,
    ValidationError,
)

__all__ = [
    "BaseAppException",
    "ConfigurationError",
    "DeploymentError",
    "LogsServiceError",
    "ScalingoAPIError",
    "ValidationError",
]
