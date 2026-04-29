"""Thin app-management handlers that delegate to the presentation controller."""
from fastapi import WebSocket

from app.handlers.base_handler import BaseHandler
from app.models import AppContext, IntentResponse
from app.presentation.websocket import AppManagementIntentController
from app.utils.websocket_helpers import WebSocketHelpers


class _BaseAppManagementHandler(BaseHandler):
    target_intent: str = ""

    def __init__(self, controller: AppManagementIntentController, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.controller = controller

    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.accepted_intent != self.target_intent:
            return False
        return await self.controller.handle(websocket, intent_response, context)


class RestartHandler(_BaseAppManagementHandler):
    target_intent = "restart"


class ScaleHandler(_BaseAppManagementHandler):
    target_intent = "scale"


class DeleteAppHandler(_BaseAppManagementHandler):
    target_intent = "delete_app"


class RenameAppHandler(_BaseAppManagementHandler):
    target_intent = "rename_app"


class ListEnvVarsHandler(_BaseAppManagementHandler):
    target_intent = "list_env_vars"


class AddEnvVarHandler(_BaseAppManagementHandler):
    target_intent = "add_env_var"
