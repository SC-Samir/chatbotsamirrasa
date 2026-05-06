from __future__ import annotations

import hashlib
import uuid
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import StructuredLogger
from app.copilot.contracts import CommandContext
from app.copilot.memory.service import MemoryService
from app.copilot.nlu.adapter import NLUAdapter
from app.copilot.orchestration.engine import CommandEngine
from app.copilot.presentation.ws_v2 import WebSocketV2Presenter

logger = StructuredLogger("ws_v2")


INTENT_TO_COMMAND: Dict[str, str] = {
    "list_apps": "apps.list",
    "get_app": "apps.get",
    "set_force_https": "apps.set_force_https",
    "set_router_logs": "apps.set_router_logs",
    "set_sticky_session": "apps.set_sticky_session",
    "change_project": "apps.change_project",
    "memory_show": "memory.show",
    "memory_forget": "memory.forget",
    "memory_pin": "memory.pin",
    "list_deployments": "deployments.list",
    "deployment_details": "deployments.details",
    "deployment_output": "deployments.output",
    "reset_deployment_cache": "deployments.cache_reset",
    "list_autoscalers": "autoscalers.list",
    "create_autoscaler": "autoscalers.create",
    "update_autoscaler": "autoscalers.update",
    "delete_autoscaler": "autoscalers.delete",
    "list_events": "events.list",
    "list_domains": "domains.list",
    "create_domain": "domains.create",
    "delete_domain": "domains.delete",
    "list_collaborators": "collaborators.list",
    "invite_collaborator": "collaborators.invite",
    "update_collaborator_role": "collaborators.update_role",
    "remove_collaborator": "collaborators.delete",
    "list_log_drains": "log_drains.list",
    "create_log_drain": "log_drains.create",
    "delete_log_drain": "log_drains.delete",
    "list_notifiers": "notifiers.list",
    "create_notifier": "notifiers.create",
    "update_notifier": "notifiers.update",
    "delete_notifier": "notifiers.delete",
    "run_one_off": "one_off.run",
    "stop_container": "containers.stop",
    "signal_container": "containers.signal",
    "list_projects": "projects.list",
    "confirm": "confirm",
}


class WebSocketV2Handler:
    def __init__(self, nlu: NLUAdapter, engine: CommandEngine, memory: MemoryService, presenter: WebSocketV2Presenter):
        self.nlu = nlu
        self.engine = engine
        self.memory = memory
        self.presenter = presenter

    async def handle_connection(self, websocket: WebSocket) -> None:
        await websocket.accept()
        session_id = websocket.headers.get("x-session-id") or str(uuid.uuid4())
        user_id = websocket.headers.get("x-user-id") or self._anonymous_user_id(websocket)

        await self.presenter.emit_system(
            websocket,
            "Connected to Scalingo Copilot ws.v2. Ask for deployment, autoscalers, memory or ops actions.",
        )

        try:
            while True:
                text = await websocket.receive_text()
                interpretation = await self.nlu.interpret(text)

                merged_entities = self.memory.merge_entities(session_id, interpretation.entities.values)
                if interpretation.memory_hints.should_persist:
                    self.memory.persist_facts(
                        user_id=user_id,
                        facts=interpretation.entities.values,
                        confidence=interpretation.memory_hints.confidence,
                    )

                if interpretation.decision.action in {"clarify", "reject"}:
                    suggestions = [c.name for c in interpretation.candidates[:3]]
                    await self.presenter.emit_system(
                        websocket,
                        (
                            "Need clarification. Please include app_name and region when relevant. "
                            f"Candidate intents: {', '.join(suggestions) if suggestions else 'none'}"
                        ),
                        status="warning",
                    )
                    continue

                intent = interpretation.decision.intent
                command = INTENT_TO_COMMAND.get(intent, intent if "." in intent else "command.unknown")

                if text.strip().lower().startswith("confirm "):
                    token = text.strip().split(" ", 1)[1]
                    command = "confirm"
                    merged_entities["confirm_token"] = token

                context = CommandContext(
                    session_id=session_id,
                    user_id=user_id,
                    app_scope=merged_entities.get("app_name"),
                    region_scope=merged_entities.get("region"),
                    trace_id=str(uuid.uuid4()),
                )

                result = self.engine.execute(command=command, entities=merged_entities, raw_text=text, context=context)
                await self.presenter.emit(websocket, result)

        except WebSocketDisconnect:
            logger.info("ws.v2 disconnected", session_id=session_id)
        except Exception as exc:
            logger.error("ws.v2 error", error=str(exc), session_id=session_id)
            await self.presenter.emit_system(websocket, f"Internal ws.v2 error: {exc}", status="error")

    @staticmethod
    def _anonymous_user_id(websocket: WebSocket) -> str:
        seed = f"{websocket.client.host if websocket.client else 'unknown'}:{websocket.client.port if websocket.client else '0'}"
        return "anon-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
