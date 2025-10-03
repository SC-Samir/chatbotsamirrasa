"""
Gestionnaire de contexte pour les handlers.
"""
from typing import Dict, Any, List, Optional
from fastapi import WebSocket
from app.models import AppContext, IntentResponse


class ContextManager:
    """Gestionnaire de contexte pour extraire et valider les entités."""
    
    @staticmethod
    def extract_entities(intent_response: IntentResponse) -> Dict[str, Any]:
        """Extrait les entités d'une réponse d'intent."""
        return {e["entity"]: e["value"] for e in intent_response.entities}
    
    @staticmethod
    def get_required_params(entities: Dict[str, Any], context: AppContext, 
                           required_fields: List[str]) -> Dict[str, Any]:
        """Récupère les paramètres requis en utilisant les entités ou le contexte."""
        params = {}
        for field in required_fields:
            params[field] = entities.get(field) or getattr(context, field, None)
        return params
    
    @staticmethod
    def update_context_from_entities(entities: Dict[str, Any], context: AppContext) -> None:
        """Met à jour le contexte avec les nouvelles entités."""
        for entity, value in entities.items():
            if hasattr(context, entity) and value:
                setattr(context, entity, value)
    
    @staticmethod
    async def send_context_reminder(websocket: WebSocket, entities: Dict[str, Any], 
                                   context: AppContext, used_fields: List[str]) -> None:
        """Envoie un rappel des valeurs de contexte utilisées."""
        used_context = []
        for field in used_fields:
            if not entities.get(field) and getattr(context, field, None):
                used_context.append(f"{field}: {getattr(context, field)}")
        
        if used_context:
            await websocket.send_text(f"💭 I remember: {', '.join(used_context)}")
    
    @staticmethod
    def validate_required_params(params: Dict[str, Any], required_fields: List[str], 
                                error_message: str) -> Optional[str]:
        """Valide que tous les paramètres requis sont présents."""
        missing = [field for field in required_fields if not params.get(field)]
        if missing:
            return f"😕 {error_message} Missing: {', '.join(missing)}"
        return None
