"""Intent handler manager with injected dependencies."""
from fastapi import WebSocket

from app.handlers.app_management_handlers import (
    AddEnvVarHandler,
    DeleteAppHandler,
    ListEnvVarsHandler,
    RenameAppHandler,
    RestartHandler,
    ScaleHandler,
)
from app.handlers.deployment_handlers import CreateAndDeployHandler, DeployHandler
from app.handlers.utility_handlers import GetLogsHandler, ShowContextHandler
from app.models import AppContext, IntentResponse
from app.presentation.websocket import AppManagementIntentController
from app.services.deployment_service import DeploymentService
from app.services.logs_service import LogsService
from app.utils.websocket_helpers import WebSocketHelpers


class IntentHandlerManager:
    """Routes intents to focused handlers."""

    def __init__(
        self,
        deployment_service: DeploymentService,
        logs_service: LogsService,
        websocket_helpers: WebSocketHelpers,
        app_management_controller: AppManagementIntentController,
    ):
        self.handlers = [
            DeployHandler(deployment_service, websocket_helpers),
            CreateAndDeployHandler(deployment_service, websocket_helpers),
            GetLogsHandler(logs_service, websocket_helpers),
            ShowContextHandler(websocket_helpers),
            RestartHandler(app_management_controller, websocket_helpers),
            ScaleHandler(app_management_controller, websocket_helpers),
            DeleteAppHandler(app_management_controller, websocket_helpers),
            RenameAppHandler(app_management_controller, websocket_helpers),
            ListEnvVarsHandler(app_management_controller, websocket_helpers),
            AddEnvVarHandler(app_management_controller, websocket_helpers),
        ]

    async def handle_intent(
        self,
        websocket: WebSocket,
        intent_response: IntentResponse,
        context: AppContext,
    ):
        for handler in self.handlers:
            result = await handler.handle(websocket, intent_response, context)
            if result:
                return result
        return False
