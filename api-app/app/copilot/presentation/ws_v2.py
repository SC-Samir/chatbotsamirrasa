from __future__ import annotations

import uuid
from typing import Dict, Any

from fastapi import WebSocket

from app.copilot.contracts import CommandResult


class WebSocketV2Presenter:
    version = "ws.v2"

    async def emit(self, websocket: WebSocket, result: CommandResult) -> None:
        envelope: Dict[str, Any] = {
            "version": self.version,
            "event_type": result.event_type,
            "status": result.status,
            "action_id": result.action_id or str(uuid.uuid4()),
            "human_message": result.human_message,
            "structured_payload": result.structured_payload,
            "next_actions": result.next_actions,
            "risk_level": result.risk_level,
        }
        await websocket.send_json(envelope)

    async def emit_system(self, websocket: WebSocket, message: str, status: str = "success") -> None:
        await self.emit(
            websocket,
            CommandResult(
                event_type="system.message",
                status=status,  # type: ignore[arg-type]
                human_message=message,
                structured_payload={},
            ),
        )
