"""
Handlers pour les intents utilitaires.
"""
from typing import Dict, Any
from fastapi import WebSocket
from app.models import AppContext, IntentResponse
from app.handlers.base_handler import BaseHandler
from app.services.logs_service import LogsService
from app.utils.websocket_helpers import WebSocketHelpers


class GetLogsHandler(BaseHandler):
    """Handler pour l'intent 'get_logs'."""
    
    def __init__(self, logs_service: LogsService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.logs_service = logs_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "get_logs":
            return False
        
        entities = self.context_manager.extract_entities(intent_response)
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To retrieve logs, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        filter_param = entities.get("filter")
        n_lines = entities.get("n")
        
        # Conversion du nombre de lignes
        n = 100  # valeur par défaut
        if n_lines:
            try:
                n = int(n_lines)
            except ValueError:
                n = 100
        
        # Détection du streaming
        stream = "stream" in intent_response.text.lower() or "streamer" in intent_response.text.lower()
        
        # Messages informatifs
        filter_info = f" (filtered by: {filter_param})" if filter_param else ""
        lines_info = f" ({n} lines)" if n != 100 else ""
        stream_info = " streaming" if stream else ""
        
        await websocket.send_text(f"📋 Retrieving logs for *{app_name}*{filter_info}{lines_info}{stream_info}...")
        
        try:
            from app.models import LogsRequest
            logs_request = LogsRequest(
                app_name=app_name,
                region=region,
                n=n,
                filter_param=filter_param,
                stream=stream
            )
            
            logs_response = await self.logs_service.get_logs_info(logs_request)
            
            if logs_response:
                if stream:
                    await websocket.send_text(f"🔄 Starting log streaming...")
                    await self.logs_service.fetch_and_display_logs(
                        websocket, logs_response.logs_url, stream_mode=True
                    )
                else:
                    await websocket.send_text(f"📄 Retrieving logs...")
                    await self.logs_service.fetch_and_display_logs(
                        websocket, logs_response.logs_url, stream_mode=False
                    )
            else:
                await self._send_error_message(websocket, f"Unable to retrieve logs URL for {app_name}.")
        except Exception as e:
            await self._send_error_message(websocket, f"Error retrieving logs: {str(e)}")
        
        return True


class ShowContextHandler(BaseHandler):
    """Handler pour l'intent 'show_context'."""
    
    def __init__(self, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "show_context":
            return False
        
        context_items = []
        if context.app_name:
            context_items.append(f"📱 App: {context.app_name}")
        if context.region:
            context_items.append(f"🌍 Region: {context.region}")
        if context.github_repo:
            context_items.append(f"📦 Repo: {context.github_repo}")
        if context.git_ref and context.git_ref != "master":
            context_items.append(f"🌿 Branch: {context.git_ref}")
        
        if context_items:
            await websocket.send_text("💭 Here's what I remember:\n" + "\n".join(context_items))
        else:
            await websocket.send_text("💭 I don't have anything in memory yet. Give me information about your app, region and repo so I can remember!")
        
        return True
