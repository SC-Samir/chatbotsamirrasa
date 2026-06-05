"""
Copilot component composition and dependency wiring.

This module provides the dependency injection composition for the copilot
components, including NLU adapter, memory service, gateway, engine, and handlers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.infrastructure.rasa import RasaClient
from app.infrastructure.scalingo import ScalingoHTTPClient, build_default_token_provider
from app.copilot.conversation.websocket_handler import WebSocketV2Handler
from app.copilot.memory import build_memory_service
from app.copilot.nlu import NLUAdapter
from app.copilot.orchestration import CommandEngine
from app.copilot.presentation.ws_v2 import WebSocketV2Presenter
from app.copilot.scalingo_ops import ScalingoOpsGateway
from app.core.logging import StructuredLogger

logger = StructuredLogger("copilot_composition")


@dataclass(frozen=True)
class CopilotComponents:
    websocket_handler: WebSocketV2Handler


def build_copilot_components() -> CopilotComponents:
    rasa_client = RasaClient(
        base_url=settings.rasa_url,
        timeout_ms=settings.rasa_timeout_ms,
        auth_token=settings.rasa_auth_token,
    )
    nlu_adapter = NLUAdapter(rasa_client)

    token_provider = build_default_token_provider()
    scalingo_client = ScalingoHTTPClient(token_provider)
    gateway = ScalingoOpsGateway(scalingo_client)

    memory = build_memory_service()
    
    # If memory service is not available, create a stub
    if memory is None:
        logger.warning("Memory service not available - using stub")
        # Create a minimal stub memory service
        from app.copilot.memory.service import MemoryService
        class StubMemoryService:
            def get(self, key: str, default: Any = None) -> Any:
                return default
            def set(self, key: str, value: Any) -> None:
                pass
            def delete(self, key: str) -> None:
                pass
            def get_session(self, session_id: str) -> dict:
                return {}
            def save_session(self, session_id: str, data: dict) -> None:
                pass
        memory = StubMemoryService()  # type: ignore
    
    engine = CommandEngine(gateway=gateway, memory=memory)
    presenter = WebSocketV2Presenter()

    websocket_handler = WebSocketV2Handler(nlu=nlu_adapter, engine=engine, memory=memory, presenter=presenter)
    return CopilotComponents(websocket_handler=websocket_handler)
