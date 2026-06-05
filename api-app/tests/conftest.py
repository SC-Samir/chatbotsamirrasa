"""
Pytest fixtures and configuration for the api-app tests.

This module provides common fixtures and test utilities used across
all test files in the project.
"""
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Set up required environment variables for tests
os.environ.setdefault("SCALINGO_API_TOKEN", "test-token")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("RASA_URL", "http://localhost:5005")


# ============================================================================
# Mock Factories
# ============================================================================

class MockOperationResult:
    """Factory for creating mock OperationResult objects."""
    
    @staticmethod
    def ok(value=None):
        """Create a successful OperationResult."""
        from app.domain.result import OperationResult
        return OperationResult.ok(value or {})
    
    @staticmethod
    def fail(error=None):
        """Create a failed OperationResult."""
        from app.domain.result import OperationResult
        from app.domain.errors import OperationError, FailureReason, ErrorCode
        if error is None:
            error = OperationError(
                reason=FailureReason.VALIDATION,
                message="Test error",
                code=ErrorCode.VALIDATION_ERROR,
            )
        return OperationResult.fail(error)


class MockScalingoHTTPClient:
    """Factory for creating mock ScalingoHTTPClient."""
    
    @staticmethod
    def create(success=True, value=None, error=None):
        """Create a mock ScalingoHTTPClient with configurable responses."""
        mock = MagicMock()
        result = MockOperationResult.ok(value) if success else MockOperationResult.fail(error)
        mock.request.return_value = result
        return mock


class MockScalingoOpsGateway:
    """Factory for creating mock ScalingoOpsGateway."""
    
    @staticmethod
    def create():
        """Create a mock ScalingoOpsGateway."""
        mock = MagicMock()
        
        # Default mock responses for common methods
        mock.apps_list.return_value = {"apps": []}
        mock.apps_get.return_value = {"app": {"name": "test-app"}}
        mock.apps_create.return_value = {"app": {"name": "test-app", "id": "app-123"}}
        mock.apps_delete.return_value = {"accepted": True}
        mock.apps_restart.return_value = {"accepted": True}
        mock.apps_update.return_value = {"app": {"name": "test-app"}}
        
        mock.deployments_list.return_value = {"deployments": []}
        mock.deployment_details.return_value = {"deployment": {"id": "deploy-123"}}
        mock.deployment_output.return_value = {"output": "logs here"}
        mock.deployments_create.return_value = {"deployment": {"id": "deploy-123"}}
        mock.deployments_rollback.return_value = {"accepted": True}
        mock.deployment_cache_reset.return_value = {"accepted": True}
        
        # Container operations
        mock.containers_list.return_value = {"containers": []}
        mock.containers_scale.return_value = {"containers": []}
        mock.containers_stop.return_value = {"accepted": True}
        mock.containers_signal.return_value = {"accepted": True}
        
        # Other operations
        mock.autoscalers_list.return_value = {"autoscalers": []}
        mock.autoscalers_create.return_value = {"autoscaler": {}}
        mock.autoscalers_update.return_value = {"autoscaler": {}}
        mock.autoscalers_delete.return_value = {"accepted": True}
        
        mock.domains_list.return_value = {"domains": []}
        mock.domains_create.return_value = {"domain": {}}
        mock.domains_delete.return_value = {"accepted": True}
        
        mock.collaborators_list.return_value = {"collaborators": []}
        mock.collaborators_invite.return_value = {"collaborator": {}}
        mock.collaborators_update.return_value = {"collaborator": {}}
        mock.collaborators_delete.return_value = {"accepted": True}
        
        mock.events_list.return_value = {"events": []}
        
        mock.env_vars_list.return_value = {"variables": []}
        mock.env_vars_set.return_value = {"variable": {}}
        mock.env_vars_unset.return_value = {"accepted": True}
        
        mock.log_drains_list.return_value = {"drains": []}
        mock.log_drains_create.return_value = {"drain": {}}
        mock.log_drains_delete.return_value = {"accepted": True}
        
        mock.notifiers_list.return_value = {"notifiers": []}
        mock.notifiers_create.return_value = {"notifier": {}}
        mock.notifiers_update.return_value = {"notifier": {}}
        mock.notifiers_delete.return_value = {"accepted": True}
        
        mock.addons_list.return_value = {"addons": []}
        mock.addons_add.return_value = {"addon": {}}
        mock.addons_remove.return_value = {"accepted": True}
        
        mock.one_off_run.return_value = {"container": {}}
        
        mock.projects_list.return_value = {"projects": []}
        
        mock.get_deployment_status.return_value = MockOperationResult.ok({
            "deployment": {"id": "deploy-123", "status": "success"}
        })
        
        mock.get_logs.return_value = MockOperationResult.ok({
            "logs_url": "http://example.com/logs",
            "parameters": {},
            "stream": False,
            "app_name": "test-app",
            "region": "osc-fr1",
        })
        
        return mock


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def mock_settings():
    """Provide mock settings for tests."""
    from app.config import Settings
    with patch.object(Settings, 'validate_startup', return_value=True):
        settings = Settings(
            scalingo_api_token="test-token",
            redis_url="redis://localhost:6379/0",
            database_url="postgresql://test:test@localhost/test",
        )
        yield settings


@pytest.fixture
def mock_scalingo_client():
    """Provide a mock ScalingoHTTPClient."""
    return MockScalingoHTTPClient.create()


@pytest.fixture
def mock_gateway():
    """Provide a mock ScalingoOpsGateway."""
    return MockScalingoOpsGateway.create()


@pytest.fixture
def mock_operation_result():
    """Provide a factory for creating mock OperationResults."""
    return MockOperationResult


@pytest.fixture
def mock_memory_service():
    """Provide a mock MemoryService."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    
    # Default mock behaviors
    mock.snapshot.return_value = MagicMock(
        session={},
        facts={},
    )
    mock.merge_entities.return_value = {}
    mock.persist_facts.return_value = None
    mock.issue_confirmation_token.return_value = {
        "token": "test-token",
        "command": "test.command",
        "payload": {},
    }
    mock.consume_confirmation_token.return_value = {
        "command": "test.command",
        "payload": {},
    }
    mock.forget.return_value = True
    mock.pin.return_value = True
    
    return mock


@pytest.fixture
def mock_nlu_adapter():
    """Provide a mock NLUAdapter."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = MagicMock()
    mock.interpret = AsyncMock(return_value=MagicMock(
        entities=MagicMock(values={}),
        memory_hints=MagicMock(should_persist=False, confidence=0.0),
        decision=MagicMock(
            intent="test.intent",
            action="accept",
            reason="accepted",
        ),
        candidates=[],
    ))
    return mock


@pytest.fixture
def mock_command_engine():
    """Provide a mock CommandEngine."""
    from unittest.mock import MagicMock
    from app.domain import FailureReason, ErrorCode, OperationError
    
    mock = MagicMock()
    
    # Default successful response
    def execute_default(command, entities, raw_text, context):
        from app.copilot.contracts import CommandResult
        return CommandResult(
            event_type=command,
            status="success",
            human_message=f"Command {command} executed",
            structured_payload={},
            next_actions=[],
            risk_level="none",
        )
    
    mock.execute = MagicMock(side_effect=execute_default)
    mock.is_destructive = MagicMock(return_value=False)
    
    return mock


@pytest.fixture
def mock_websocket_presenter():
    """Provide a mock WebSocketV2Presenter."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = MagicMock()
    mock.emit = AsyncMock()
    mock.emit_system = AsyncMock()
    
    return mock


# ============================================================================
# Test Utilities
# ============================================================================

class TestHelpers:
    """Helper methods for testing."""
    
    @staticmethod
    def create_logs_request(app_name="test-app", region="osc-fr1", n=100):
        """Create a LogsRequest for testing."""
        from app.models import LogsRequest
        from app.domain import Region
        return LogsRequest(
            app_name=app_name,
            region=Region(region),
            n=n,
        )
    
    @staticmethod
    def create_command_context(
        session_id="test-session",
        user_id="test-user",
        app_scope=None,
        region_scope=None,
    ):
        """Create a CommandContext for testing."""
        from app.copilot.contracts import CommandContext
        return CommandContext(
            session_id=session_id,
            user_id=user_id,
            app_scope=app_scope,
            region_scope=region_scope,
        )
    
    @staticmethod
    def create_command_request(
        command="test.command",
        entities=None,
        raw_text="test",
        context=None,
    ):
        """Create a CommandRequest for testing."""
        from app.copilot.contracts import CommandRequest
        return CommandRequest(
            command=command,
            entities=entities or {},
            raw_text=raw_text,
            context=context or TestHelpers.create_command_context(),
        )
    
    @staticmethod
    def create_command_result(
        event_type="test",
        status="success",
        human_message="Test message",
        structured_payload=None,
        next_actions=None,
        risk_level="none",
        action_id=None,
    ):
        """Create a CommandResult for testing."""
        from app.copilot.contracts import CommandResult
        return CommandResult(
            event_type=event_type,
            status=status,
            human_message=human_message,
            structured_payload=structured_payload or {},
            next_actions=next_actions or [],
            risk_level=risk_level,
            action_id=action_id,
        )


# Make helpers available at module level
helpers = TestHelpers()
