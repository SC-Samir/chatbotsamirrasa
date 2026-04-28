"""Interfaces and protocols for layered architecture."""
from typing import Any, Optional, Protocol, TypeVar

from app.domain import OperationResult

CommandT = TypeVar("CommandT")
ResultT = TypeVar("ResultT")


class UseCaseProtocol(Protocol[CommandT, ResultT]):
    def execute(self, command: CommandT) -> OperationResult[ResultT]:
        ...


class WebSocketHandlerProtocol(Protocol):
    async def handle_connection(self, websocket) -> None:
        ...


class IntentHandlerProtocol(Protocol):
    async def handle(self, websocket, intent_response, context) -> bool:
        ...


class GatewayProtocol(Protocol):
    """Marker protocol for infrastructure gateways."""

    def __repr__(self) -> str:
        ...
