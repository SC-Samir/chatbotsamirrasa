"""WebSocket presentation helpers and message contract."""
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from fastapi import WebSocket


@dataclass(frozen=True)
class WSMessage:
    kind: str
    message: str
    data: Optional[Dict[str, Any]] = None


class WebSocketPresenter:
    async def send(
        self,
        websocket: WebSocket,
        kind: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = WSMessage(kind=kind, message=message, data=data)
        await websocket.send_text(json.dumps(asdict(payload)))

    async def info(self, websocket: WebSocket, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        await self.send(websocket, "info", message, data)

    async def success(self, websocket: WebSocket, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        await self.send(websocket, "success", message, data)

    async def warning(self, websocket: WebSocket, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        await self.send(websocket, "warning", message, data)

    async def error(self, websocket: WebSocket, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        await self.send(websocket, "error", message, data)

    async def progress(self, websocket: WebSocket, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        await self.send(websocket, "progress", message, data)
