"""
Handler de base pour tous les handlers d'intent.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from fastapi import WebSocket
from app.models import AppContext, IntentResponse
from app.utils.context_manager import ContextManager
from app.utils.websocket_helpers import WebSocketHelpers
from app.utils.error_handler import ErrorHandler
from app.exceptions.handler_exceptions import ValidationException


class BaseHandler(ABC):
    """Classe de base pour tous les handlers d'intent."""
    
    def __init__(self, websocket_helpers: WebSocketHelpers):
        self.websocket_helpers = websocket_helpers
        self.context_manager = ContextManager()
    
    @abstractmethod
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext):
        """Traite un intent."""
        pass
    
    async def _handle_common_validation(self, websocket: WebSocket, intent_response: IntentResponse, 
                                     context: AppContext, required_fields: list, 
                                     error_message: str) -> Optional[Dict[str, Any]]:
        """Gestion commune de la validation."""
        try:
            entities = self.context_manager.extract_entities(intent_response)
            params = self.context_manager.get_required_params(entities, context, required_fields)
            
            # Validation des paramètres requis
            validation_error = self.context_manager.validate_required_params(
                params, required_fields, error_message
            )
            if validation_error:
                missing_fields = [field for field in required_fields if not params.get(field)]
                raise ValidationException(validation_error, missing_fields)
            
            # Mise à jour du contexte
            self.context_manager.update_context_from_entities(entities, context)
            
            # Rappel du contexte utilisé
            await self.context_manager.send_context_reminder(
                websocket, entities, context, required_fields
            )
            
            return params
        except ValidationException as e:
            await ErrorHandler.handle_validation_error(websocket, e)
            return None
        except Exception as e:
            await ErrorHandler.handle_generic_error(websocket, e, "Validation")
            return None
    
    async def _send_success_message(self, websocket: WebSocket, message: str) -> None:
        """Envoie un message de succès."""
        await websocket.send_text(f"✅ {message}")
    
    async def _send_error_message(self, websocket: WebSocket, message: str) -> None:
        """Envoie un message d'erreur."""
        await websocket.send_text(f"❌ {message}")
    
    async def _send_info_message(self, websocket: WebSocket, message: str) -> None:
        """Envoie un message d'information."""
        await websocket.send_text(f"💭 {message}")
