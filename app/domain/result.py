"""Typed result contract for application use-cases."""
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from app.domain.errors import OperationError

T = TypeVar("T")


@dataclass(frozen=True)
class OperationResult(Generic[T]):
    success: bool
    value: Optional[T] = None
    error: Optional[OperationError] = None

    @classmethod
    def ok(cls, value: Optional[T] = None) -> "OperationResult[T]":
        return cls(success=True, value=value, error=None)

    @classmethod
    def fail(cls, error: OperationError) -> "OperationResult[T]":
        return cls(success=False, value=None, error=error)
