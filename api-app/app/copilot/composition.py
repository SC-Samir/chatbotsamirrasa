from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.infrastructure.rasa import RasaClient
from app.infrastructure.scalingo import ScalingoHTTPClient, build_default_token_provider
from app.copilot.conversation.websocket_handler import WebSocketV2Handler
from app.copilot.memory import build_memory_service
from app.copilot.nlu import NLUAdapter
from app.copilot.orchestration import CommandEngine
from app.copilot.presentation.ws_v2 import WebSocketV2Presenter
from app.copilot.scalingo_ops import ScalingoOpsGateway


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
    engine = CommandEngine(gateway=gateway, memory=memory)
    presenter = WebSocketV2Presenter()

    websocket_handler = WebSocketV2Handler(nlu=nlu_adapter, engine=engine, memory=memory, presenter=presenter)
    return CopilotComponents(websocket_handler=websocket_handler)
