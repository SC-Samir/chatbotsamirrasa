"""
Domain errors and failure reasons.

This module defines the error types and failure reasons used throughout
the application for consistent error handling and reporting.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class FailureReason(str, Enum):
    """Reasons for operation failures."""
    VALIDATION = "validation"
    AUTH = "auth"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    TRANSIENT = "transient"
    UPSTREAM = "upstream"
    UNKNOWN = "unknown"


class ErrorCode(str, Enum):
    """
    Standard error codes for consistent error identification.
    
    These codes are used across the application to identify and categorize
    different types of errors, making it easier to handle and monitor them.
    """
    # Validation errors
    VALIDATION_ERROR = "E001"
    DOMAIN_VALIDATION_ERROR = "E002"
    
    # Authentication and authorization
    AUTH_ERROR = "E100"
    PERMISSION_ERROR = "E101"
    
    # Not found errors
    RESOURCE_NOT_FOUND = "E200"
    
    # Conflict errors
    RESOURCE_CONFLICT = "E300"
    ALREADY_EXISTS = "E301"
    
    # Transient errors
    TRANSIENT_ERROR = "E400"
    TIMEOUT_ERROR = "E401"
    RATE_LIMIT_ERROR = "E402"
    
    # Upstream errors
    UPSTREAM_ERROR = "E500"
    SERVICE_UNAVAILABLE = "E501"
    
    # Configuration errors
    CONFIGURATION_ERROR = "E600"
    MISSING_CONFIGURATION = "E601"
    INVALID_CONFIGURATION = "E602"
    
    # Application errors
    INTERNAL_ERROR = "E700"
    UNEXPECTED_ERROR = "E701"


@dataclass(frozen=True)
class ErrorContext:
    """
    Context information for errors.
    
    Contains metadata about when and where an error occurred, useful for
    debugging and monitoring.
    """
    error_id: UUID
    timestamp: datetime
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    @classmethod
    def create(cls, request_id: Optional[str] = None, user_id: Optional[str] = None, session_id: Optional[str] = None) -> "ErrorContext":
        """Create a new error context with auto-generated values."""
        return cls(
            error_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )


@dataclass(frozen=True)
class OperationError:
    """
    Error that occurred during an operation.
    
    This is the primary error type used in the domain layer to represent
    failures that occur during business operations.
    """
    reason: FailureReason
    message: str
    code: ErrorCode
    status_code: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ErrorContext] = None
    
    def with_context(self, request_id: Optional[str] = None, user_id: Optional[str] = None, session_id: Optional[str] = None) -> "OperationError":
        """Add context to this error."""
        return OperationError(
            reason=self.reason,
            message=self.message,
            code=self.code,
            status_code=self.status_code,
            details=self.details,
            context=ErrorContext.create(request_id, user_id, session_id),
        )


class DomainValidationError(ValueError):
    """Raised when a value object is invalid."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, code: ErrorCode = ErrorCode.DOMAIN_VALIDATION_ERROR):
        self.message = message
        self.field = field
        self.value = value
        self.code = code
        super().__init__(message)


class OperationExecutionError(Exception):
    """Exception wrapper to map OperationError in HTTP middleware."""

    def __init__(self, error: OperationError):
        self.error = error
        super().__init__(error.message)
