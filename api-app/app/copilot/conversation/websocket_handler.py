from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import StructuredLogger
from app.copilot.conversation.connection_manager import (
    get_connection_manager,
    ConnectionStatus,
    WebSocketVersion,
)
from app.copilot.contracts import CommandContext
from app.copilot.memory.service import MemoryService
from app.copilot.nlu.adapter import NLUAdapter
from app.copilot.orchestration.engine import CommandEngine
from app.copilot.presentation.ws_v2 import WebSocketV2Presenter

logger = StructuredLogger("ws_v2")

# Authentication configuration
WS_AUTH_TOKEN_HEADER = "x-ws-auth-token"


INTENT_TO_COMMAND: Dict[str, str] = {
    # Intent aliases for backward compatibility
    "deploy": "deployments.create",
    "create_and_deploy": "deployments.create",
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
    # New commands for Phase 4.5
    "app_stats": "apps.stats",
    "app_backups": "apps.backups",
    "create_backup": "apps.backups.create",
    "download_backup": "apps.backups.download",
    "list_regions": "regions.list",
    "scalingo_status": "scalingo.status",
    "batch_execute": "batch.execute",
}

SUPPORTED_WS_COMMANDS = {
    "apps.list", "apps.get", "apps.create", "apps.restart", "apps.delete", "apps.rename", "apps.set_force_https",
    "apps.set_router_logs", "apps.set_sticky_session", "apps.change_project", "apps.stats", "apps.backups",
    "apps.backups.create", "apps.backups.download", "deployments.list", "deployments.details",
    "deployments.output", "deployments.create", "deployments.rollback", "deployments.cache_reset", "autoscalers.list",
    "autoscalers.create", "autoscalers.update", "autoscalers.delete", "events.list", "domains.list", "domains.create",
    "domains.delete", "collaborators.list", "collaborators.invite", "collaborators.update_role", "collaborators.delete",
    "log_drains.list", "log_drains.create", "log_drains.delete", "notifiers.list", "notifiers.create", "notifiers.update",
    "notifiers.delete", "one_off.run", "containers.list", "containers.scale", "containers.stop", "containers.signal",
    "projects.list", "env_vars.list", "env_vars.set", "env_vars.unset", "addons.list", "addons.add", "addons.remove",
    "memory.show", "memory.forget", "memory.pin", "confirm",
    # New commands for Phase 4.5
    "regions.list",
    "scalingo.status",
    "batch.execute",
}


class WebSocketV2Handler:
    def __init__(self, nlu: NLUAdapter, engine: CommandEngine, memory: MemoryService, presenter: WebSocketV2Presenter):
        self.nlu = nlu
        self.engine = engine
        self.memory = memory
        self.presenter = presenter
        self._connection_manager = None
        
    async def _get_connection_manager(self) -> Any:
        """Lazy load connection manager."""
        if self._connection_manager is None:
            self._connection_manager = await get_connection_manager()
        return self._connection_manager

    async def handle_connection(self, websocket: WebSocket) -> None:
        await websocket.accept()
        session_id = websocket.headers.get("x-session-id") or str(uuid.uuid4())
        user_id = websocket.headers.get("x-user-id") or self._anonymous_user_id(websocket)
        
        # Register connection with connection manager
        connection_manager = await self._get_connection_manager()
        connection = await connection_manager.register_connection(
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            version=WebSocketVersion.V2,
        )
        
        # Record connection in message history
        await connection_manager.record_message(
            connection_id=connection.connection_id,
            direction="system",
            message_type="text",
            content="Connected to Scalingo Copilot ws.v2.",
            command="system.connect",
            status="success",
        )

        await self.presenter.emit_system(
            websocket,
            self._msg("Connected to Scalingo Copilot ws.v2.", "Connecte au Copilot Scalingo ws.v2.", "en"),
        )

        # Start ping/pong monitoring in background
        ping_task = asyncio.create_task(self._ping_pong_monitor(connection.connection_id, websocket))

        try:
            while True:
                # Check for authentication message
                try:
                    text = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Timeout occurred, continue to check for ping/pong
                    continue
                
                # Handle system commands (ping, pong, auth)
                if text.strip().lower() == "ping":
                    await connection_manager.record_pong(connection.connection_id)
                    await self._handle_ping(websocket, connection.connection_id)
                    continue
                elif text.strip().lower() == "pong":
                    await connection_manager.record_pong(connection.connection_id)
                    continue
                elif text.startswith("auth "):
                    # Handle authentication
                    await self._handle_authentication(text, websocket, connection.connection_id)
                    continue
                
                # Record incoming message
                await connection_manager.record_message(
                    connection_id=connection.connection_id,
                    direction="in",
                    message_type="text",
                    content=text,
                    command=None,
                    status="received",
                )
                
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
                    raw_entities_for_command = self._entities_for_command(
                        "apps.create",
                        merged_for_legacy,
                        current_for_legacy,
                    )
                    # Keep only fields relevant for create+deploy flow.
                    app_name = str(raw_entities_for_command.get("app_name") or "").strip()
                    region = str(raw_entities_for_command.get("region") or "").strip()
                    github_repo = str(raw_entities_for_command.get("github_repo") or "").strip()
                    source_url = str(raw_entities_for_command.get("source_url") or "").strip()
                    git_ref = str(raw_entities_for_command.get("git_ref") or "").strip()
                    explicit_git_ref = self._extract_explicit_git_ref(text)
                    if explicit_git_ref:
                        git_ref = explicit_git_ref
                    if not git_ref or git_ref in {":", "-", ".", "/"}:
                        git_ref = "main"
                    entities_for_command = {
                        "app_name": app_name,
                        "region": region,
                        "github_repo": github_repo,
                        "source_url": source_url,
                        "git_ref": git_ref,
                    }
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

                    deploy_entities = {
                        "app_name": entities_for_command.get("app_name"),
                        "region": entities_for_command.get("region"),
                        "github_repo": entities_for_command.get("github_repo"),
                        "source_url": entities_for_command.get("source_url"),
                        "git_ref": entities_for_command.get("git_ref"),
                    }
                    deploy_result = self.engine.execute(
                        command="deployments.create",
                        entities=deploy_entities,
                        raw_text=text,
                        context=context,
                    )
                    await self.presenter.emit(websocket, deploy_result)
                    continue
                if command == "legacy.show_logs":
                    normalized = self._normalize_entities(merged_entities)
                    current = self._normalize_entities(dict(interpretation.entities.values))
                    if fallback_entities:
                        current = self._normalize_entities(fallback_entities)
                    entities_for_command = self._entities_for_command("deployments.list", normalized, current)
                    context = CommandContext(
                        session_id=session_id,
                        user_id=user_id,
                        app_scope=entities_for_command.get("app_name"),
                        region_scope=entities_for_command.get("region"),
                        trace_id=str(uuid.uuid4()),
                    )
                    list_result = self.engine.execute(
                        command="deployments.list",
                        entities=entities_for_command,
                        raw_text=text,
                        context=context,
                    )
                    if list_result.status != "success":
                        await self.presenter.emit(websocket, list_result)
                        continue
                    deployments = list_result.structured_payload.get("deployments") or []
                    if not deployments:
                        await self.presenter.emit_system(
                            websocket,
                            self._msg(
                                "No deployments found for this app.",
                                "Aucun deploiement trouve pour cette app.",
                                lang,
                            ),
                            status="warning",
                        )
                        continue
                    latest_deployment = deployments[0] if isinstance(deployments[0], dict) else {}
                    deployment_id = str(latest_deployment.get("id") or "").strip()
                    if not deployment_id:
                        await self.presenter.emit_system(
                            websocket,
                            self._msg(
                                "Unable to determine latest deployment id.",
                                "Impossible de determiner l'identifiant du dernier deploiement.",
                                lang,
                            ),
                            status="warning",
                        )
                        continue
                    output_entities = {
                        "app_name": entities_for_command.get("app_name"),
                        "region": entities_for_command.get("region"),
                        "deployment_id": deployment_id,
                    }
                    output_result = self.engine.execute(
                        command="deployments.output",
                        entities=output_entities,
                        raw_text=text,
                        context=context,
                    )
                    await self.presenter.emit(websocket, output_result)
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
                
                # Record outgoing message
                await connection_manager.record_message(
                    connection_id=connection.connection_id,
                    direction="out",
                    message_type="json",
                    content=result,
                    command=command,
                    status=result.status,
                )

        except WebSocketDisconnect:
            # Clean up connection on disconnect
            try:
                await connection_manager.unregister_connection(connection.connection_id)
                ping_task.cancel()
            except Exception:
                pass
            logger.info("ws.v2 disconnected", session_id=session_id, connection_id=connection.connection_id)
        except asyncio.CancelledError:
            # Handle task cancellation
            try:
                await connection_manager.unregister_connection(connection.connection_id)
            except Exception:
                pass
            logger.info("ws.v2 connection cancelled", session_id=session_id, connection_id=connection.connection_id)
        except Exception as exc:
            # Record error
            try:
                await connection_manager.record_error(connection.connection_id, str(exc))
            except Exception:
                pass
            logger.error("ws.v2 error", error=str(exc), session_id=session_id, connection_id=connection.connection_id)
            try:
                await self.presenter.emit_system(websocket, f"Internal ws.v2 error: {exc}", status="error")
            except Exception:
                pass

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
        explicit_command = re.search(r"\b([a-z_]+\.[a-z_]+)\b", s, flags=re.IGNORECASE)
        if explicit_command:
            candidate = explicit_command.group(1).lower()
            if candidate in SUPPORTED_WS_COMMANDS:
                return candidate, {}
        patterns = [
            (
                r"(?:create\s+and\s+deploy|create\s+app\s+and\s+deploy|create\s+then\s+deploy)\s+([a-z0-9][a-z0-9-]*)\s+(?:to|on|in)\s+([a-z0-9-]+)\s+(?:with|from|using)\s+(https?://[^\s]+)(?:\s+(?:(?:on|from)\s+)?(?:branch|ref)\s+([A-Za-z0-9._/-]+))?",
                "legacy.create_and_deploy",
                ("app_name", "region", "github_repo", "git_ref"),
            ),
            (r"(?:show|list|get)\s+env(?:ironment)?\s*(?:vars|variables)?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "env_vars.list", ("app_name", "region")),
            (r"(?:unset|delete|remove)\s+env\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:for|on)\s+([a-z0-9-]+)\s+(?:in|on)\s+([a-z0-9-]+)", "env_vars.unset", ("env_name", "app_name", "region")),
            (r"(?:restart|redeploy)\s+(?:app\s+)?([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.restart", ("app_name", "region")),
            (r"(?:list|show|get)\s+addons\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "addons.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+containers\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "containers.list", ("app_name", "region")),
            (r"(?:show|get|list)\s+logs\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "legacy.show_logs", ("app_name", "region")),
            (r"(?:list|show|get)\s+apps?\s+(?:on|in)\s+([a-z0-9-]+)", "apps.list", ("region",)),
            (r"(?:get|show)\s+app\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.get", ("app_name", "region")),
            (r"(?:delete|remove)\s+app\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.delete", ("app_name", "region")),
            (r"(?:restart|redeploy)\s+app\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.restart", ("app_name", "region")),
            (r"(?:list|show|get)\s+deployments?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "deployments.list", ("app_name", "region")),
            (r"(?:show|get)\s+deployment\s+([A-Za-z0-9-]+)\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "deployments.details", ("deployment_id", "app_name", "region")),
            (r"(?:show|get)\s+deployment\s+output\s+([A-Za-z0-9-]+)\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "deployments.output", ("deployment_id", "app_name", "region")),
            (r"(?:reset|clear)\s+deployment\s+cache\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "deployments.cache_reset", ("app_name", "region")),
            (r"(?:list|show|get)\s+domains?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "domains.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+events?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "events.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+collaborators?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "collaborators.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+log\s*drains?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "log_drains.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+notifiers?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "notifiers.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+autoscalers?\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "autoscalers.list", ("app_name", "region")),
            (r"(?:list|show|get)\s+projects?\s+(?:on|in)\s+([a-z0-9-]+)", "projects.list", ("region",)),
            (r"(?:show|get|list)\s+memory\b", "memory.show", ()),
            # New commands for Phase 4.5
            (r"(?:show|get)\s+app\s+stats\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.stats", ("app_name", "region")),
            (r"(?:list|show|get)\s+backups\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.backups", ("app_name", "region")),
            (r"(?:create|make)\s+backup\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.backups.create", ("app_name", "region")),
            (r"(?:download|get)\s+backup\s+([A-Za-z0-9-]+)\s+(?:for|of)\s+([a-z0-9-]+)\s+(?:on|in)\s+([a-z0-9-]+)", "apps.backups.download", ("backup_id", "app_name", "region")),
            (r"(?:list|show|get)\s+regions?\b", "regions.list", ()),
            (r"(?:show|get|check)\s+scalingo\s+status\b", "scalingo.status", ()),
            (r"(?:run|execute)\s+batch\s+(?:commands|operations)?\b", "batch.execute", ()),
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
    def _extract_explicit_git_ref(text: str) -> Optional[str]:
        m = re.search(r"(?:^|\s)(?:(?:on|from)\s+)?(?:branch|ref)\s+([A-Za-z0-9._/-]+)(?:\s|$)", text, flags=re.IGNORECASE)
        if not m:
            return None
        ref = m.group(1).strip().lower()
        return ref or None

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

    async def _ping_pong_monitor(self, connection_id: str, websocket: WebSocket) -> None:
        """Send periodic ping messages to keep connection alive."""
        connection_manager = await self._get_connection_manager()
        ping_interval = 20.0  # seconds
        
        try:
            while True:
                await asyncio.sleep(ping_interval)
                
                # Check if connection is still active
                connection = await connection_manager.get_connection(connection_id)
                if not connection or connection.status in [ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR]:
                    break
                
                # Send ping
                try:
                    await connection_manager.record_ping(connection_id)
                    await websocket.send_text("ping")
                except Exception as e:
                    logger.warning(
                        "Failed to send ping",
                        connection_id=connection_id,
                        error=str(e),
                    )
                    break
        except asyncio.CancelledError:
            logger.debug("Ping/pong monitor cancelled", connection_id=connection_id)
        except Exception as e:
            logger.error("Ping/pong monitor error", connection_id=connection_id, error=str(e))

    async def _handle_ping(self, websocket: WebSocket, connection_id: str) -> None:
        """Handle ping message from client."""
        connection_manager = await self._get_connection_manager()
        try:
            await websocket.send_text("pong")
            await connection_manager.record_pong(connection_id)
            logger.debug("Received ping, sent pong", connection_id=connection_id)
        except Exception as e:
            logger.warning("Failed to send pong", connection_id=connection_id, error=str(e))

    async def _handle_authentication(self, text: str, websocket: WebSocket, connection_id: str) -> None:
        """Handle authentication message from client."""
        connection_manager = await self._get_connection_manager()
        
        # Extract token from "auth <token>" message
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            await self.presenter.emit_system(
                websocket,
                self._msg(
                    "Authentication failed: no token provided.",
                    "Echec de l'authentification: aucun jeton fourni.",
                    "en",
                ),
                status="error",
            )
            return
        
        token = parts[1].strip()
        
        # Validate token and authenticate
        # In production, you would validate against your authentication service
        # For now, we'll accept any non-empty token
        if token:
            success = await connection_manager.authenticate_connection(connection_id, token)
            if success:
                await self.presenter.emit_system(
                    websocket,
                    self._msg(
                        "Authentication successful.",
                        "Authentification reussie.",
                        "en",
                    ),
                    status="success",
                )
                logger.info("WebSocket authenticated", connection_id=connection_id)
            else:
                await self.presenter.emit_system(
                    websocket,
                    self._msg(
                        "Authentication failed.",
                        "Echec de l'authentification.",
                        "en",
                    ),
                    status="error",
                )
        else:
            await self.presenter.emit_system(
                websocket,
                self._msg(
                    "Authentication failed: invalid token.",
                    "Echec de l'authentification: jeton invalide.",
                    "en",
                ),
                status="error",
            )
