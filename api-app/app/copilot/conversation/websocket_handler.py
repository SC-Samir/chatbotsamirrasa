from __future__ import annotations

import hashlib
import re
import uuid
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import StructuredLogger
from app.copilot.contracts import CommandContext
from app.copilot.memory.service import MemoryService
from app.copilot.nlu.adapter import NLUAdapter
from app.copilot.orchestration.engine import CommandEngine
from app.copilot.presentation.ws_v2 import WebSocketV2Presenter

logger = StructuredLogger("ws_v2")


INTENT_TO_COMMAND: Dict[str, str] = {
    # Legacy intent aliases
    "deploy": "deployments.create",
    "create_and_deploy": "legacy.create_and_deploy",
    "restart": "apps.restart",
    "scale": "containers.scale",
    "delete_app": "apps.delete",
    "rename_app": "apps.rename",
    "list_env_vars": "env_vars.list",
    "add_env_var": "env_vars.set",
    "show_context": "memory.show",
    # ws.v2 intents
    "list_apps": "apps.list",
    "get_app": "apps.get",
    "create_app": "apps.create",
    "restart_app": "apps.restart",
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
    "create_deployment": "deployments.create",
    "reset_deployment_cache": "deployments.cache_reset",
    "rollback_deployment": "deployments.rollback",
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
    "list_containers": "containers.list",
    "scale_container": "containers.scale",
    "stop_container": "containers.stop",
    "signal_container": "containers.signal",
    "list_projects": "projects.list",
    "list_env_vars": "env_vars.list",
    "set_env_var": "env_vars.set",
    "unset_env_var": "env_vars.unset",
    "list_addons": "addons.list",
    "add_addon": "addons.add",
    "remove_addon": "addons.remove",
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
            self._msg("Connected to Scalingo Copilot ws.v2.", "Connecte au Copilot Scalingo ws.v2.", "en"),
        )

        try:
            while True:
                text = await websocket.receive_text()
                lang = self._detect_lang(text)
                interpretation = await self.nlu.interpret(text)

                merged_entities = self.memory.merge_entities(session_id, interpretation.entities.values)
                if interpretation.memory_hints.should_persist:
                    self.memory.persist_facts(
                        user_id=user_id,
                        facts=interpretation.entities.values,
                        confidence=interpretation.memory_hints.confidence,
                    )

                command = self._resolve_command(interpretation.decision.intent, text)
                fallback_entities: Dict[str, str] = {}
                if not command:
                    command, fallback_entities = self._rule_based_fallback(text)
                    if fallback_entities:
                        merged_entities.update(fallback_entities)

                if interpretation.decision.action in {"clarify", "reject"} and not command:
                    suggestions = [c.name for c in interpretation.candidates[:3]]
                    await self.presenter.emit_system(
                        websocket,
                        self._msg(
                            f"Need clarification. Candidate intents: {', '.join(suggestions) if suggestions else 'none'}",
                            f"J'ai besoin de clarification. Intentions candidates: {', '.join(suggestions) if suggestions else 'aucune'}",
                            lang,
                        ),
                        status="warning",
                    )
                    continue

                if text.strip().lower().startswith("confirm "):
                    token = text.strip().split(" ", 1)[1]
                    command = "confirm"
                    merged_entities["confirm_token"] = token

                if not command:
                    await self.presenter.emit_system(
                        websocket,
                        self._msg(
                            "Command not recognized.",
                            "Commande non reconnue.",
                            lang,
                        ),
                        status="warning",
                    )
                    continue

                if command == "legacy.create_and_deploy":
                    merged_for_legacy = self._normalize_entities(merged_entities)
                    current_for_legacy = self._normalize_entities(dict(interpretation.entities.values))
                    if fallback_entities:
                        # When regex fallback matched, trust those extracted entities over noisy NLU entities.
                        current_for_legacy = self._normalize_entities(fallback_entities)
                    entities_for_command = self._entities_for_command(
                        "apps.create",
                        merged_for_legacy,
                        current_for_legacy,
                    )
                    context = CommandContext(
                        session_id=session_id,
                        user_id=user_id,
                        app_scope=entities_for_command.get("app_name"),
                        region_scope=entities_for_command.get("region"),
                        trace_id=str(uuid.uuid4()),
                    )
                    create_result = self.engine.execute(
                        command="apps.create",
                        entities=entities_for_command,
                        raw_text=text,
                        context=context,
                    )
                    await self.presenter.emit(websocket, create_result)
                    if create_result.status not in {"success"}:
                        continue

                    deploy_entities = dict(entities_for_command)
                    deploy_result = self.engine.execute(
                        command="deployments.create",
                        entities=deploy_entities,
                        raw_text=text,
                        context=context,
                    )
                    await self.presenter.emit(websocket, deploy_result)
                    continue

                current_entities = dict(interpretation.entities.values)
                if fallback_entities:
                    # For regex-matched commands, use extracted fallback entities as authoritative current entities.
                    current_entities = fallback_entities
                entities_for_command = self._entities_for_command(
                    command,
                    self._normalize_entities(merged_entities),
                    self._normalize_entities(current_entities),
                )

                context = CommandContext(
                    session_id=session_id,
                    user_id=user_id,
                    app_scope=entities_for_command.get("app_name"),
                    region_scope=entities_for_command.get("region"),
                    trace_id=str(uuid.uuid4()),
                )

                result = self.engine.execute(command=command, entities=entities_for_command, raw_text=text, context=context)
                if result.event_type == "command.validation_error":
                    missing = result.structured_payload.get("missing_entities", [])
                    result = type(result)(
                        event_type=result.event_type,
                        status=result.status,
                        human_message=self._msg(
                            f"Missing fields for {command}: {', '.join(missing)}",
                            f"Champs manquants pour {command}: {', '.join(missing)}",
                            lang,
                        ),
                        structured_payload=result.structured_payload,
                        next_actions=result.next_actions,
                        risk_level=result.risk_level,
                        action_id=result.action_id,
                    )
                await self.presenter.emit(websocket, result)

        except WebSocketDisconnect:
            logger.info("ws.v2 disconnected", session_id=session_id)
        except Exception as exc:
            logger.error("ws.v2 error", error=str(exc), session_id=session_id)
            await self.presenter.emit_system(websocket, f"Internal ws.v2 error: {exc}", status="error")

    def _entities_for_command(self, command: str, merged: Dict[str, object], current: Dict[str, object]) -> Dict[str, object]:
        if command == "confirm":
            return merged
        if self.engine.is_destructive(command):
            safe = dict(merged)
            if "app_name" not in current or "region" not in current:
                safe.pop("app_name", None)
                safe.pop("region", None)
            safe.update(current)
            return safe
        safe = dict(merged)
        safe.update(current)
        return safe

    @staticmethod
    def _normalize_entities(raw: Dict[str, object]) -> Dict[str, object]:
        """Normalize legacy entity keys/values to ws.v2 command schema."""
        entities = dict(raw)

        if "container_name" in entities and "container_type" not in entities:
            entities["container_type"] = entities.get("container_name")
        if "container_amount" in entities and "amount" not in entities:
            entities["amount"] = entities.get("container_amount")

        if "variable_name" in entities and "env_name" not in entities:
            entities["env_name"] = entities.get("variable_name")
        if "variable_value" in entities and "env_value" not in entities:
            entities["env_value"] = entities.get("variable_value")

        scope = entities.get("scope")
        if isinstance(scope, str):
            entities["scope"] = [s.strip() for s in scope.split(",") if s.strip()]

        return entities

    @staticmethod
    def _resolve_command(intent: str, text: str) -> Optional[str]:
        command = INTENT_TO_COMMAND.get(intent)
        if command:
            return command
        if "." in intent:
            return intent
        if text.strip().lower().startswith("confirm "):
            return "confirm"
        return None

    @staticmethod
    def _rule_based_fallback(text: str) -> tuple[Optional[str], Dict[str, str]]:
        s = text.strip()
        patterns = [
            (
                r"(?:create\s+and\s+deploy|create\s+app\s+and\s+deploy|create\s+then\s+deploy)\s+([a-z0-9][a-z0-9-]*)\s+(?:to|on|in)\s+([a-z0-9-]+)\s+(?:with|from|using)\s+(https?://[^\s]+)(?:\s+(?:branch|ref)\s+([A-Za-z0-9._/-]+))?",
                "legacy.create_and_deploy",
                ("app_name", "region", "github_repo", "git_ref"),
            ),
            (r"(?:show|list|get)\s+env(?:ironment)?\s*(?:vars|variables)?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "env_vars.list", ("app_name", "region")),
            (r"(?:unset|delete|remove)\s+env\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:for|on)\s+([a-z0-9-]+)\s+(?:in|on)\s+([a-z0-9-]+)", "env_vars.unset", ("env_name", "app_name", "region")),
            (r"(?:restart|redeploy)\s+(?:app\s+)?([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.restart", ("app_name", "region")),
            (r"(?:list|show|get)\s+addons\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "addons.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+containers\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "containers.list", ("app_name", "region")),
        ]
        for pattern, command, keys in patterns:
            m = re.search(pattern, s, flags=re.IGNORECASE)
            if m:
                entities: Dict[str, str] = {}
                for i, key in enumerate(keys):
                    val = m.group(i + 1) if i + 1 <= (m.lastindex or 0) else None
                    if not val:
                        continue
                    entities[key] = val.lower() if key != "github_repo" else val
                return command, entities
        return None, {}

    @staticmethod
    def _detect_lang(text: str) -> str:
        low = text.lower()
        fr_hits = ["bonjour", "merci", "supprime", "redemarre", "pour", "avec", "sur", "app", "variables"]
        en_hits = ["please", "delete", "restart", "show", "list", "with", "for", "on"]
        fr_score = sum(1 for token in fr_hits if token in low)
        en_score = sum(1 for token in en_hits if token in low)
        if fr_score >= en_score:
            return "fr"
        return "en"

    @staticmethod
    def _msg(en: str, fr: str, lang: str) -> str:
        if lang == "fr":
            return f"{fr} / {en}"
        return f"{en} / {fr}"

    @staticmethod
    def _anonymous_user_id(websocket: WebSocket) -> str:
        seed = f"{websocket.client.host if websocket.client else 'unknown'}:{websocket.client.port if websocket.client else '0'}"
        return "anon-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
