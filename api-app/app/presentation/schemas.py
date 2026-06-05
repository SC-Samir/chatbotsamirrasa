"""
Response schemas and DTOs for API endpoints.

This module provides standardized response formats, pagination, filtering,
and request/response schemas for the API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field, validator


class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"


class ErrorCode(str, Enum):
    """Standard error codes."""
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    BAD_GATEWAY = "bad_gateway"
    SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass
class Pagination:
    """Pagination information for list responses."""
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False
    
    @classmethod
    def from_query(cls, page: int = 1, per_page: int = 20) -> "Pagination":
        """Create pagination from query parameters."""
        page = max(1, page)
        per_page = max(1, min(100, per_page))  # Limit to 100 per page
        return cls(page=page, per_page=per_page)
    
    def update_from_total(self, total: int) -> "Pagination":
        """Update pagination with total count."""
        total_pages = max(1, (total + self.per_page - 1) // self.per_page)
        has_next = self.page < total_pages
        has_previous = self.page > 1
        return cls(
            page=self.page,
            per_page=self.per_page,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": self.total,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


@dataclass
class SortOrder:
    """Sort order for list responses."""
    field: str = ""
    direction: str = "asc"  # asc or desc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "direction": self.direction,
        }


@dataclass
class FilterCondition:
    """Filter condition for list responses."""
    field: str
    operator: str  # eq, neq, gt, gte, lt, lte, contains, startswith, endswith, in, not_in
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }


@dataclass
class ListQuery:
    """Query parameters for list endpoints."""
    pagination: Pagination = field(default_factory=Pagination)
    filters: List[FilterCondition] = field(default_factory=list)
    sort: List[SortOrder] = field(default_factory=list)
    search: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pagination": self.pagination.to_dict(),
            "filters": [f.to_dict() for f in self.filters],
            "sort": [s.to_dict() for s in self.sort],
            "search": self.search,
        }


T = TypeVar('T')


@dataclass
class PaginatedResponse(Generic[T]):
    """Standard paginated response format."""
    status: str = "success"
    data: List[T] = field(default_factory=list)
    pagination: Pagination = field(default_factory=Pagination)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "data": self.data,
            "pagination": self.pagination.to_dict(),
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


@dataclass
class StandardResponse(Generic[T]):
    """Standard response format for non-paginated endpoints."""
    status: str = "success"
    data: Optional[T] = None
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "status": self.status,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }
        if self.message:
            result["message"] = self.message
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class ErrorResponse:
    """Standard error response format."""
    status: str = "error"
    error: ErrorCode = ErrorCode.INTERNAL_ERROR
    message: str = "An internal error occurred"
    details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "status": self.status,
            "error": self.error.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class ValidationErrorResponse:
    """Validation error response format."""
    status: str = "validation_error"
    error: ErrorCode = ErrorCode.VALIDATION_ERROR
    message: str = "Validation failed"
    errors: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "status": self.status,
            "error": self.error.value,
            "message": self.message,
            "errors": self.errors,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }
        return result


# Pydantic models for request/response validation

class PaginationQuery(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1, le=1000, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class SortQuery(BaseModel):
    """Sort query parameters."""
    field: str = Field(default="", description="Field to sort by")
    direction: str = Field(default="asc", description="Sort direction (asc or desc)")
    
    @validator('direction')
    def validate_direction(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('direction must be either "asc" or "desc"')
        return v


class FilterQuery(BaseModel):
    """Filter query parameters."""
    field: str = Field(default="", description="Field to filter on")
    operator: str = Field(default="eq", description="Filter operator")
    value: Any = Field(default=None, description="Filter value")


class SearchQuery(BaseModel):
    """Search query parameters."""
    q: Optional[str] = Field(default=None, description="Search query")
    search_fields: Optional[List[str]] = Field(default=None, description="Fields to search in")


class ListRequest(BaseModel):
    """Standard list request parameters."""
    pagination: PaginationQuery = Field(default_factory=PaginationQuery)
    sort: Optional[List[SortQuery]] = Field(default=None)
    filters: Optional[List[FilterQuery]] = Field(default=None)
    search: Optional[SearchQuery] = Field(default=None)


class AppResponse(BaseModel):
    """Application response schema."""
    id: Optional[str] = None
    name: str
    region: str
    url: Optional[str] = None
    git_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status: Optional[str] = None
    
    class Config:
        from_attributes = True


class DeploymentResponse(BaseModel):
    """Deployment response schema."""
    id: str
    app_id: str
    app_name: str
    region: str
    status: str
    git_ref: str
    created_at: str
    updated_at: str
    finished_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    version: str
    timestamp: str
    checks: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    """Metrics response schema."""
    system: Dict[str, Any] = Field(default_factory=dict)
    counters: Dict[str, Any] = Field(default_factory=dict)
    gauges: Dict[str, Any] = Field(default_factory=dict)
    histograms: Dict[str, Any] = Field(default_factory=dict)
    timers: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class MemoryFactResponse(BaseModel):
    """Memory fact response schema."""
    key: str
    value: Any
    confidence: float
    pinned: bool
    source: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: int = 1
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class MemoryAnalyticsResponse(BaseModel):
    """Memory analytics response schema."""
    total_facts: int = 0
    pinned_facts: int = 0
    total_sessions: int = 0
    average_confidence: float = 0.0
    by_source: Dict[str, int] = Field(default_factory=dict)
    by_tag: Dict[str, int] = Field(default_factory=dict)
    storage_size_bytes: int = 0
    
    class Config:
        from_attributes = True


# Response format helpers

def create_success_response(
    data: Optional[Any] = None,
    message: str = "",
    request_id: str = "",
) -> StandardResponse[Any]:
    """Create a success response."""
    return StandardResponse(
        status=ResponseStatus.SUCCESS.value,
        data=data,
        message=message,
        request_id=request_id,
    )


def create_error_response(
    error: ErrorCode,
    message: str,
    request_id: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
    """Create an error response."""
    return ErrorResponse(
        status="error",
        error=error,
        message=message,
        details=details,
        request_id=request_id,
    )


def create_validation_error_response(
    message: str = "Validation failed",
    errors: Optional[List[Dict[str, Any]]] = None,
    request_id: str = "",
) -> ValidationErrorResponse:
    """Create a validation error response."""
    return ValidationErrorResponse(
        errors=errors or [],
        message=message,
        request_id=request_id,
    )


def create_paginated_response(
    data: List[Any],
    pagination: Pagination,
    request_id: str = "",
) -> PaginatedResponse[Any]:
    """Create a paginated response."""
    return PaginatedResponse(
        status=ResponseStatus.SUCCESS.value,
        data=data,
        pagination=pagination,
        request_id=request_id,
    )


# Helper functions for pagination

def paginate_data(data: List[Any], page: int = 1, per_page: int = 20) -> tuple[List[Any], Pagination]:
    """
    Paginate a list of data.
    
    Args:
        data: List of data to paginate
        page: Current page number
        per_page: Items per page
    
    Returns:
        Tuple of (paginated_data, pagination_info)
    """
    total = len(data)
    pagination = Pagination.from_query(page, per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_data = data[start_idx:end_idx]
    updated_pagination = pagination.update_from_total(total)
    
    return paginated_data, updated_pagination


def apply_filters(
    data: List[Dict[str, Any]],
    filters: List[FilterCondition],
) -> List[Dict[str, Any]]:
    """
    Apply filters to a list of data.
    
    Args:
        data: List of dictionaries to filter
        filters: List of filter conditions
    
    Returns:
        Filtered list of data
    """
    filtered = data
    
    for filter_cond in filters:
        filtered = [
            item for item in filtered
            if _apply_filter_condition(item, filter_cond.field, filter_cond.operator, filter_cond.value)
        ]
    
    return filtered


def _apply_filter_condition(
    item: Dict[str, Any],
    field: str,
    operator: str,
    value: Any,
) -> bool:
    """Apply a single filter condition to an item."""
    if field not in item:
        return False
    
    item_value = item[field]
    
    if operator == "eq":
        return item_value == value
    elif operator == "neq":
        return item_value != value
    elif operator == "gt":
        return item_value > value
    elif operator == "gte":
        return item_value >= value
    elif operator == "lt":
        return item_value < value
    elif operator == "lte":
        return item_value <= value
    elif operator == "contains":
        return isinstance(item_value, str) and value in item_value
    elif operator == "startswith":
        return isinstance(item_value, str) and item_value.startswith(value)
    elif operator == "endswith":
        return isinstance(item_value, str) and item_value.endswith(value)
    elif operator == "in":
        return item_value in value
    elif operator == "not_in":
        return item_value not in value
    else:
        return False
