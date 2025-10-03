"""
Gestionnaire d'intents refactorisé.
"""
from typing import Dict, Any
from fastapi import WebSocket
from app.models import AppContext, IntentResponse
from app.scalingo_manager import ScalingoManager
from app.services.logs_service import LogsService
from app.services.deployment_service import DeploymentService
from app.services.app_management_service import AppManagementService
from app.utils.websocket_helpers import WebSocketHelpers
from app.handlers.deployment_handlers import DeployHandler, CreateAndDeployHandler
from app.handlers.app_management_handlers import RestartHandler, ScaleHandler, DeleteAppHandler, RenameAppHandler, ListEnvVarsHandler, AddEnvVarHandler
from app.handlers.utility_handlers import GetLogsHandler, ShowContextHandler


class IntentHandlerManager:
    """Gestionnaire d'intents refactorisé."""
    
    def __init__(self, scalingo_manager: ScalingoManager, logs_service: LogsService):
        self.scalingo_manager = scalingo_manager
        self.logs_service = logs_service
        
        # Initialisation des services
        self.deployment_service = DeploymentService(scalingo_manager)
        self.app_service = AppManagementService(scalingo_manager)
        self.websocket_helpers = WebSocketHelpers(scalingo_manager)
        
        # Initialisation des handlers
        self.handlers = [
            DeployHandler(self.deployment_service, self.websocket_helpers),
            CreateAndDeployHandler(self.deployment_service, self.websocket_helpers),
            GetLogsHandler(logs_service, self.websocket_helpers),
            ShowContextHandler(self.websocket_helpers),
            RestartHandler(self.app_service, self.websocket_helpers),
            ScaleHandler(self.app_service, self.websocket_helpers),
            DeleteAppHandler(self.app_service, self.websocket_helpers),
            RenameAppHandler(self.app_service, self.websocket_helpers),
            ListEnvVarsHandler(self.app_service, self.websocket_helpers),
            AddEnvVarHandler(self.app_service, self.websocket_helpers),
        ]
    
    async def handle_intent(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext):
        """Traite un intent en utilisant le handler approprié."""
        for handler in self.handlers:
            result = await handler.handle(websocket, intent_response, context)
            if result:
                return result
        return False