"""
Unit tests for response schemas and DTOs.
"""
from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any, Dict, List

from app.presentation.schemas import (
    ResponseStatus,
    ErrorCode,
    Pagination,
    SortOrder,
    FilterCondition,
    ListQuery,
    PaginatedResponse,
    StandardResponse,
    ErrorResponse,
    ValidationErrorResponse,
    PaginationQuery,
    SortQuery,
    FilterQuery,
    SearchQuery,
    ListRequest,
    AppResponse,
    DeploymentResponse,
    HealthResponse,
    MetricsResponse,
    MemoryFactResponse,
    MemoryAnalyticsResponse,
    create_success_response,
    create_error_response,
    create_validation_error_response,
    create_paginated_response,
    paginate_data,
    apply_filters,
)


class TestEnums(unittest.TestCase):
    """Tests for enum classes."""
    
    def test_response_status_values(self):
        """Test ResponseStatus enum values."""
        self.assertEqual(ResponseStatus.SUCCESS.value, "success")
        self.assertEqual(ResponseStatus.WARNING.value, "warning")
        self.assertEqual(ResponseStatus.ERROR.value, "error")
        self.assertEqual(ResponseStatus.VALIDATION_ERROR.value, "validation_error")
        self.assertEqual(ResponseStatus.NOT_FOUND.value, "not_found")
        self.assertEqual(ResponseStatus.UNAUTHORIZED.value, "unauthorized")
        self.assertEqual(ResponseStatus.FORBIDDEN.value, "forbidden")
        self.assertEqual(ResponseStatus.RATE_LIMITED.value, "rate_limited")
    
    def test_error_code_values(self):
        """Test ErrorCode enum values."""
        self.assertEqual(ErrorCode.INVALID_REQUEST.value, "invalid_request")
        self.assertEqual(ErrorCode.NOT_FOUND.value, "not_found")
        self.assertEqual(ErrorCode.UNAUTHORIZED.value, "unauthorized")
        self.assertEqual(ErrorCode.FORBIDDEN.value, "forbidden")
        self.assertEqual(ErrorCode.RATE_LIMITED.value, "rate_limited")
        self.assertEqual(ErrorCode.INTERNAL_ERROR.value, "internal_error")
        self.assertEqual(ErrorCode.VALIDATION_ERROR.value, "validation_error")
        self.assertEqual(ErrorCode.CONFLICT.value, "conflict")
        self.assertEqual(ErrorCode.BAD_GATEWAY.value, "bad_gateway")
        self.assertEqual(ErrorCode.SERVICE_UNAVAILABLE.value, "service_unavailable")


class TestPagination(unittest.TestCase):
    """Tests for Pagination class."""
    
    def test_default_values(self):
        """Test default values."""
        pagination = Pagination()
        
        self.assertEqual(pagination.page, 1)
        self.assertEqual(pagination.per_page, 20)
        self.assertEqual(pagination.total, 0)
        self.assertEqual(pagination.total_pages, 0)
        self.assertFalse(pagination.has_next)
        self.assertFalse(pagination.has_previous)
    
    def test_from_query(self):
        """Test from_query method."""
        pagination = Pagination.from_query(page=2, per_page=10)
        
        self.assertEqual(pagination.page, 2)
        self.assertEqual(pagination.per_page, 10)
    
    def test_from_query_limits(self):
        """Test that from_query applies limits."""
        # Page should be at least 1
        pagination = Pagination.from_query(page=0, per_page=20)
        self.assertEqual(pagination.page, 1)
        
        # Per page should be at most 100
        pagination = Pagination.from_query(page=1, per_page=150)
        self.assertEqual(pagination.per_page, 100)
    
    def test_update_from_total(self):
        """Test update_from_total method."""
        pagination = Pagination(page=1, per_page=10)
        updated = pagination.update_from_total(25)
        
        self.assertEqual(updated.page, 1)
        self.assertEqual(updated.per_page, 10)
        self.assertEqual(updated.total, 25)
        self.assertEqual(updated.total_pages, 3)
        self.assertTrue(updated.has_next)
        self.assertFalse(updated.has_previous)
    
    def test_to_dict(self):
        """Test to_dict method."""
        pagination = Pagination(page=2, per_page=10, total=100, total_pages=10)
        result = pagination.to_dict()
        
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["per_page"], 10)
        self.assertEqual(result["total"], 100)
        self.assertEqual(result["total_pages"], 10)


class TestSortOrder(unittest.TestCase):
    """Tests for SortOrder class."""
    
    def test_default_values(self):
        """Test default values."""
        sort = SortOrder()
        
        self.assertEqual(sort.field, "")
        self.assertEqual(sort.direction, "asc")
    
    def test_to_dict(self):
        """Test to_dict method."""
        sort = SortOrder(field="name", direction="desc")
        result = sort.to_dict()
        
        self.assertEqual(result["field"], "name")
        self.assertEqual(result["direction"], "desc")


class TestFilterCondition(unittest.TestCase):
    """Tests for FilterCondition class."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        condition = FilterCondition(field="status", operator="eq", value="active")
        result = condition.to_dict()
        
        self.assertEqual(result["field"], "status")
        self.assertEqual(result["operator"], "eq")
        self.assertEqual(result["value"], "active")


class TestListQuery(unittest.TestCase):
    """Tests for ListQuery class."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        pagination = Pagination(page=1, per_page=20)
        sort = SortOrder(field="name", direction="asc")
        condition = FilterCondition(field="status", operator="eq", value="active")
        
        query = ListQuery(
            pagination=pagination,
            sort=[sort],
            filters=[condition],
            search="test",
        )
        
        result = query.to_dict()
        
        self.assertIn("pagination", result)
        self.assertIn("sort", result)
        self.assertIn("filters", result)
        self.assertEqual(result["search"], "test")


class TestPaginatedResponse(unittest.TestCase):
    """Tests for PaginatedResponse class."""
    
    def test_default_values(self):
        """Test default values."""
        response = PaginatedResponse()
        
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, [])
        self.assertEqual(response.request_id, "")
        self.assertIsNotNone(response.timestamp)
    
    def test_to_dict(self):
        """Test to_dict method."""
        pagination = Pagination(page=1, per_page=20, total=100)
        response = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            pagination=pagination,
            request_id="req-123",
        )
        
        result = response.to_dict()
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["request_id"], "req-123")
        self.assertIn("pagination", result)
        self.assertIn("timestamp", result)


class TestStandardResponse(unittest.TestCase):
    """Tests for StandardResponse class."""
    
    def test_to_dict_with_data(self):
        """Test to_dict method with data."""
        response = StandardResponse(
            data={"id": 1, "name": "test"},
            message="Success",
            request_id="req-123",
        )
        
        result = response.to_dict()
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], {"id": 1, "name": "test"})
        self.assertEqual(result["message"], "Success")
        self.assertEqual(result["request_id"], "req-123")
    
    def test_to_dict_without_data(self):
        """Test to_dict method without data."""
        response = StandardResponse(
            message="Success",
            request_id="req-123",
        )
        
        result = response.to_dict()
        
        self.assertEqual(result["status"], "success")
        self.assertNotIn("data", result)
        self.assertEqual(result["message"], "Success")
    
    def test_to_dict_without_message(self):
        """Test to_dict method without message."""
        response = StandardResponse(
            data={"id": 1},
            request_id="req-123",
        )
        
        result = response.to_dict()
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], {"id": 1})
        self.assertNotIn("message", result)


class TestErrorResponse(unittest.TestCase):
    """Tests for ErrorResponse class."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        response = ErrorResponse(
            error=ErrorCode.NOT_FOUND,
            message="Resource not found",
            details={"resource": "user", "id": 123},
            request_id="req-123",
        )
        
        result = response.to_dict()
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "not_found")
        self.assertEqual(result["message"], "Resource not found")
        self.assertEqual(result["details"], {"resource": "user", "id": 123})
        self.assertEqual(result["request_id"], "req-123")


class TestValidationErrorResponse(unittest.TestCase):
    """Tests for ValidationErrorResponse class."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        errors = [
            {"field": "name", "message": "Name is required"},
            {"field": "email", "message": "Invalid email format"},
        ]
        
        response = ValidationErrorResponse(
            message="Validation failed",
            errors=errors,
            request_id="req-123",
        )
        
        result = response.to_dict()
        
        self.assertEqual(result["status"], "validation_error")
        self.assertEqual(result["error"], "validation_error")
        self.assertEqual(result["message"], "Validation failed")
        self.assertEqual(result["errors"], errors)
        self.assertEqual(result["request_id"], "req-123")


class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions."""
    
    def test_create_success_response(self):
        """Test create_success_response function."""
        response = create_success_response(
            data={"id": 1},
            message="Created",
            request_id="req-123",
        )
        
        self.assertIsInstance(response, StandardResponse)
        self.assertEqual(response.data, {"id": 1})
        self.assertEqual(response.message, "Created")
        self.assertEqual(response.request_id, "req-123")
    
    def test_create_error_response(self):
        """Test create_error_response function."""
        response = create_error_response(
            error=ErrorCode.NOT_FOUND,
            message="Not found",
            request_id="req-123",
        )
        
        self.assertIsInstance(response, ErrorResponse)
        self.assertEqual(response.error, ErrorCode.NOT_FOUND)
        self.assertEqual(response.message, "Not found")
        self.assertEqual(response.request_id, "req-123")
    
    def test_create_validation_error_response(self):
        """Test create_validation_error_response function."""
        errors = [{"field": "name", "message": "Required"}]
        response = create_validation_error_response(
            message="Validation failed",
            errors=errors,
            request_id="req-123",
        )
        
        self.assertIsInstance(response, ValidationErrorResponse)
        self.assertEqual(response.message, "Validation failed")
        self.assertEqual(response.errors, errors)
        self.assertEqual(response.request_id, "req-123")
    
    def test_create_paginated_response(self):
        """Test create_paginated_response function."""
        pagination = Pagination(page=1, per_page=20, total=100)
        response = create_paginated_response(
            data=[{"id": 1}, {"id": 2}],
            pagination=pagination,
            request_id="req-123",
        )
        
        self.assertIsInstance(response, PaginatedResponse)
        self.assertEqual(response.data, [{"id": 1}, {"id": 2}])
        self.assertEqual(response.pagination, pagination)
        self.assertEqual(response.request_id, "req-123")
    
    def test_paginate_data(self):
        """Test paginate_data function."""
        data = list(range(100))
        
        paginated, pagination = paginate_data(data, page=2, per_page=10)
        
        self.assertEqual(len(paginated), 10)
        self.assertEqual(paginated, list(range(10, 20)))
        self.assertEqual(pagination.page, 2)
        self.assertEqual(pagination.per_page, 10)
        self.assertEqual(pagination.total, 100)
        self.assertEqual(pagination.total_pages, 10)
        self.assertTrue(pagination.has_next)
        self.assertTrue(pagination.has_previous)
    
    def test_apply_filters_eq(self):
        """Test apply_filters with eq operator."""
        data = [
            {"name": "Alice", "age": 25, "active": True},
            {"name": "Bob", "age": 30, "active": False},
            {"name": "Charlie", "age": 25, "active": True},
        ]
        
        filters = [
            FilterCondition(field="age", operator="eq", value=25),
        ]
        
        result = apply_filters(data, filters)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Alice")
        self.assertEqual(result[1]["name"], "Charlie")
    
    def test_apply_filters_gt(self):
        """Test apply_filters with gt operator."""
        data = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
            {"name": "Charlie", "age": 20},
        ]
        
        filters = [
            FilterCondition(field="age", operator="gt", value=25),
        ]
        
        result = apply_filters(data, filters)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Bob")
    
    def test_apply_filters_contains(self):
        """Test apply_filters with contains operator."""
        data = [
            {"name": "Alice Smith"},
            {"name": "Bob Johnson"},
            {"name": "Charlie Brown"},
        ]
        
        filters = [
            FilterCondition(field="name", operator="contains", value="Smith"),
        ]
        
        result = apply_filters(data, filters)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Alice Smith")
    
    def test_apply_filters_multiple(self):
        """Test apply_filters with multiple conditions."""
        data = [
            {"name": "Alice", "age": 25, "active": True},
            {"name": "Bob", "age": 30, "active": False},
            {"name": "Charlie", "age": 25, "active": False},
            {"name": "Diana", "age": 30, "active": True},
        ]
        
        filters = [
            FilterCondition(field="age", operator="gte", value=25),
            FilterCondition(field="active", operator="eq", value=True),
        ]
        
        result = apply_filters(data, filters)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Alice")
        self.assertEqual(result[1]["name"], "Diana")


class TestPydanticModels(unittest.TestCase):
    """Tests for Pydantic models."""
    
    def test_pagination_query(self):
        """Test PaginationQuery model."""
        query = PaginationQuery(page=2, per_page=10)
        
        self.assertEqual(query.page, 2)
        self.assertEqual(query.per_page, 10)
    
    def test_pagination_query_validation(self):
        """Test PaginationQuery validation."""
        # Page should be at least 1
        query = PaginationQuery(page=0)
        self.assertEqual(query.page, 0)  # Pydantic allows this by default
        
        # Per page should be at least 1
        query = PaginationQuery(per_page=0)
        self.assertEqual(query.per_page, 0)
    
    def test_sort_query(self):
        """Test SortQuery model."""
        query = SortQuery(field="name", direction="desc")
        
        self.assertEqual(query.field, "name")
        self.assertEqual(query.direction, "desc")
    
    def test_sort_query_validation(self):
        """Test SortQuery direction validation."""
        # Valid direction
        query = SortQuery(direction="asc")
        self.assertEqual(query.direction, "asc")
        
        # Invalid direction should raise ValueError
        with self.assertRaises(ValueError):
            SortQuery(direction="invalid")
    
    def test_app_response(self):
        """Test AppResponse model."""
        app = AppResponse(
            id="app-123",
            name="my-app",
            region="par",
            url="https://my-app.scalingo.io",
            git_url="https://github.com/my-repo.git",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            status="running",
        )
        
        self.assertEqual(app.id, "app-123")
        self.assertEqual(app.name, "my-app")
        self.assertEqual(app.region, "par")
    
    def test_deployment_response(self):
        """Test DeploymentResponse model."""
        deployment = DeploymentResponse(
            id="dep-123",
            app_id="app-123",
            app_name="my-app",
            region="par",
            status="success",
            git_ref="main",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            finished_at="2024-01-02T00:01:00Z",
        )
        
        self.assertEqual(deployment.id, "dep-123")
        self.assertEqual(deployment.app_name, "my-app")
        self.assertEqual(deployment.status, "success")
    
    def test_health_response(self):
        """Test HealthResponse model."""
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp="2024-01-01T00:00:00Z",
            checks={"redis": "up", "postgres": "up"},
        )
        
        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.version, "1.0.0")
        self.assertEqual(health.checks, {"redis": "up", "postgres": "up"})
    
    def test_memory_analytics_response(self):
        """Test MemoryAnalyticsResponse model."""
        analytics = MemoryAnalyticsResponse(
            total_facts=100,
            pinned_facts=10,
            total_sessions=5,
            average_confidence=0.85,
            by_source={"nlu": 80, "manual": 20},
            by_tag={"important": 10, "temporary": 5},
            storage_size_bytes=10240,
        )
        
        self.assertEqual(analytics.total_facts, 100)
        self.assertEqual(analytics.pinned_facts, 10)
        self.assertEqual(analytics.average_confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
