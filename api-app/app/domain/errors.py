"""Domain errors and failure reasons."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class FailureReason(str, Enum):
    VALIDATION = "validation"
    AUTH = "auth"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    TRANSIENT = "transient"
    UPSTREAM = "upstream"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OperationError:
    reason: FailureReason
    message: str
    status_code: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


class DomainValidationError(ValueError):
    """Raised when a value object is invalid."""


class OperationExecutionError(Exception):
    """Exception wrapper to map OperationError in HTTP middleware."""

    def __init__(self, error: OperationError):
        self.error = error
        super().__init__(error.message)
