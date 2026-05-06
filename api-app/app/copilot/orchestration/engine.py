from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from app.copilot.contracts import CommandContext, CommandRequest, CommandResult
from app.copilot.memory.service import MemoryService
from app.copilot.scalingo_ops.gateway import ScalingoOpsGateway

Handler = Callable[[CommandRequest], CommandResult]


@dataclass(frozen=True)
class CommandMetadata:
    required_entities: Tuple[str, ...] = ()
    risky: bool = False
    idempotent: bool = True
    dry_run_support: bool = False
    requires_app_region: bool = False


class CommandEngine:
    def __init__(self, gateway: ScalingoOpsGateway, memory: MemoryService):
        self.gateway = gateway
        self.memory = memory
        self.registry: Dict[str, Handler] = {
            "apps.list": self._apps_list,
            "apps.get": self._apps_get,
            "apps.set_force_https": self._apps_set_force_https,
            "apps.set_router_logs": self._apps_set_router_logs,
            "apps.set_sticky_session": self._apps_set_sticky_session,
            "apps.change_project": self._apps_change_project,
            "memory.show": self._memory_show,
            "memory.forget": self._memory_forget,
            "memory.pin": self._memory_pin,
            "deployments.list": self._deployments_list,
            "deployments.details": self._deployments_details,
            "deployments.output": self._deployments_output,
            "deployments.cache_reset": self._deployments_cache_reset,
            "autoscalers.list": self._autoscalers_list,
            "autoscalers.create": self._autoscalers_create,
            "autoscalers.update": self._autoscalers_update,
            "autoscalers.delete": self._autoscalers_delete,
            "events.list": self._events_list,
            "domains.list": self._domains_list,
            "domains.create": self._domains_create,
            "domains.delete": self._domains_delete,
            "collaborators.list": self._collaborators_list,
            "collaborators.invite": self._collaborators_invite,
            "collaborators.update_role": self._collaborators_update_role,
            "collaborators.delete": self._collaborators_delete,
            "log_drains.list": self._log_drains_list,
            "log_drains.create": self._log_drains_create,
            "log_drains.delete": self._log_drains_delete,
            "notifiers.list": self._notifiers_list,
            "notifiers.create": self._notifiers_create,
            "notifiers.update": self._notifiers_update,
            "notifiers.delete": self._notifiers_delete,
            "one_off.run": self._one_off_run,
            "containers.stop": self._containers_stop,
            "containers.signal": self._containers_signal,
            "projects.list": self._projects_list,
            "confirm": self._confirm,
        }
        self.metadata: Dict[str, CommandMetadata] = {
            "apps.list": CommandMetadata(required_entities=("region",)),
            "apps.get": CommandMetadata(requires_app_region=True),
            "apps.set_force_https": CommandMetadata(required_entities=("enabled",), requires_app_region=True, risky=True, idempotent=False),
            "apps.set_router_logs": CommandMetadata(required_entities=("enabled",), requires_app_region=True, risky=True, idempotent=False),
            "apps.set_sticky_session": CommandMetadata(required_entities=("enabled",), requires_app_region=True, risky=True, idempotent=False),
            "apps.change_project": CommandMetadata(required_entities=("project_id",), requires_app_region=True, risky=True, idempotent=False),
            "memory.show": CommandMetadata(),
            "memory.forget": CommandMetadata(required_entities=("memory_key",), idempotent=False),
            "memory.pin": CommandMetadata(required_entities=("memory_key",), idempotent=False),
            "deployments.list": CommandMetadata(requires_app_region=True),
            "deployments.details": CommandMetadata(required_entities=("deployment_id",), requires_app_region=True),
            "deployments.output": CommandMetadata(required_entities=("deployment_id",), requires_app_region=True),
            "deployments.cache_reset": CommandMetadata(requires_app_region=True, risky=True, idempotent=False),
            "autoscalers.list": CommandMetadata(requires_app_region=True),
            "autoscalers.create": CommandMetadata(required_entities=("container_type", "min_containers", "max_containers", "metric", "target"), requires_app_region=True, risky=True, idempotent=False),
            "autoscalers.update": CommandMetadata(required_entities=("autoscaler_id",), requires_app_region=True, risky=True, idempotent=False),
            "autoscalers.delete": CommandMetadata(required_entities=("autoscaler_id",), requires_app_region=True, risky=True, idempotent=False),
            "events.list": CommandMetadata(requires_app_region=True),
            "domains.list": CommandMetadata(requires_app_region=True),
            "domains.create": CommandMetadata(required_entities=("domain",), requires_app_region=True, risky=True, idempotent=False),
            "domains.delete": CommandMetadata(required_entities=("domain",), requires_app_region=True, risky=True, idempotent=False),
            "collaborators.list": CommandMetadata(requires_app_region=True),
            "collaborators.invite": CommandMetadata(required_entities=("email",), requires_app_region=True, risky=True, idempotent=False),
            "collaborators.update_role": CommandMetadata(required_entities=("collaborator_id", "is_limited"), requires_app_region=True, risky=True, idempotent=False),
            "collaborators.delete": CommandMetadata(required_entities=("collaborator_id",), requires_app_region=True, risky=True, idempotent=False),
            "log_drains.list": CommandMetadata(requires_app_region=True),
            "log_drains.create": CommandMetadata(required_entities=("drain_type",), requires_app_region=True, risky=True, idempotent=False),
            "log_drains.delete": CommandMetadata(required_entities=("drain_id",), requires_app_region=True, risky=True, idempotent=False),
            "notifiers.list": CommandMetadata(requires_app_region=True),
            "notifiers.create": CommandMetadata(required_entities=("notifier_name", "platform_id"), requires_app_region=True, risky=True, idempotent=False),
            "notifiers.update": CommandMetadata(required_entities=("notifier_id",), requires_app_region=True, risky=True, idempotent=False),
            "notifiers.delete": CommandMetadata(required_entities=("notifier_id",), requires_app_region=True, risky=True, idempotent=False),
            "one_off.run": CommandMetadata(required_entities=("command",), requires_app_region=True, risky=True, idempotent=False),
            "containers.stop": CommandMetadata(required_entities=("container_id",), requires_app_region=True, risky=True, idempotent=False),
            "containers.signal": CommandMetadata(required_entities=("container_id", "signal"), requires_app_region=True, risky=True, idempotent=False),
            "projects.list": CommandMetadata(required_entities=("region",)),
            "confirm": CommandMetadata(required_entities=("confirm_token",), idempotent=False),
        }

    def execute(self, command: str, entities: Dict[str, Any], raw_text: str, context: CommandContext) -> CommandResult:
        req = CommandRequest(command=command, entities=entities, raw_text=raw_text, context=context)
        meta = self.metadata.get(command)
        if meta and meta.risky and not entities.get("confirm_token"):
            token = self.memory.issue_confirmation_token(
                session_id=context.session_id,
                command=command,
                payload={"entities": entities, "raw_text": raw_text},
            )
            return CommandResult(
                event_type="command.confirmation_required",
                status="requires_confirmation",
                human_message=f"High-risk action detected. Re-send with confirm token: {token}",
                structured_payload={"confirm_token": token, "command": command},
                next_actions=[f"confirm {token}"],
                risk_level="high",
            )
        if meta:
            missing = self._missing_entities(meta, req)
            if missing:
                return CommandResult(
                    event_type="command.validation_error",
                    status="warning",
                    human_message=f"Missing required fields: {', '.join(missing)}",
                    structured_payload={"missing_entities": missing, "command": command},
                    next_actions=[f"provide {field}" for field in missing],
                    risk_level="low",
                )
        handler = self.registry.get(command)
        if not handler:
            return CommandResult(
                event_type="command.unknown",
                status="warning",
                human_message=f"Unsupported command '{command}'.",
                structured_payload={"supported": sorted(self.registry.keys())},
            )
        return handler(req)

    def _resolve_app_region(self, req: CommandRequest) -> Tuple[str, str]:
        snapshot = self.memory.snapshot(req.context.user_id, req.context.session_id)
        entities = dict(snapshot.session.get("entities", {}))
        entities.update(snapshot.facts)
        entities.update(req.entities)

        app_name = str(entities.get("app_name") or "")
        region = str(entities.get("region") or req.context.region_scope or "")
        if not app_name or not region:
            raise ValueError("app_name and region are required")
        return app_name, region

    def _missing_entities(self, meta: CommandMetadata, req: CommandRequest) -> Tuple[str, ...]:
        missing = []
        if meta.requires_app_region:
            try:
                self._resolve_app_region(req)
            except ValueError:
                if not req.entities.get("app_name"):
                    missing.append("app_name")
                if not req.entities.get("region") and not req.context.region_scope:
                    missing.append("region")
        for key in meta.required_entities:
            if req.entities.get(key) is None or str(req.entities.get(key)).strip() == "":
                missing.append(key)
        return tuple(sorted(set(missing)))

    @staticmethod
    def _as_bool(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            norm = value.strip().lower()
            if norm in {"true", "1", "yes", "on", "enabled"}:
                return True
            if norm in {"false", "0", "no", "off", "disabled"}:
                return False
        return None

    def _apps_list(self, req: CommandRequest) -> CommandResult:
        region = str(req.entities.get("region") or req.context.region_scope or "")
        payload = self.gateway.apps_list(region)
        return CommandResult("apps.list", "success", "Applications loaded", payload)

    def _apps_get(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.apps_get(app_name, region)
        return CommandResult("apps.get", "success", "Application loaded", payload)

    def _apps_update_field(self, req: CommandRequest, field_name: str, message: str) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        enabled = self._as_bool(req.entities.get("enabled"))
        if enabled is None:
            return CommandResult("apps.update", "warning", "enabled must be a boolean")
        payload = self.gateway.apps_update(app_name, region, {field_name: enabled})
        return CommandResult("apps.update", "success", message, payload, risk_level="high")

    def _apps_set_force_https(self, req: CommandRequest) -> CommandResult:
        return self._apps_update_field(req, "force_https", "Application force_https updated")

    def _apps_set_router_logs(self, req: CommandRequest) -> CommandResult:
        return self._apps_update_field(req, "router_logs", "Application router_logs updated")

    def _apps_set_sticky_session(self, req: CommandRequest) -> CommandResult:
        return self._apps_update_field(req, "sticky_session", "Application sticky_session updated")

    def _apps_change_project(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        project_id = str(req.entities.get("project_id") or "")
        payload = self.gateway.apps_update(app_name, region, {"project_id": project_id})
        return CommandResult("apps.change_project", "success", "Application project updated", payload, risk_level="high")

    def _memory_show(self, req: CommandRequest) -> CommandResult:
        snap = self.memory.snapshot(req.context.user_id, req.context.session_id)
        return CommandResult(
            event_type="memory.snapshot",
            status="success",
            human_message="Current memory snapshot",
            structured_payload={"session": snap.session, "facts": snap.facts},
        )

    def _memory_forget(self, req: CommandRequest) -> CommandResult:
        key = str(req.entities.get("memory_key") or "")
        if not key:
            return CommandResult("memory.forget", "warning", "memory_key is required")
        ok = self.memory.forget(req.context.user_id, key)
        return CommandResult(
            event_type="memory.forget",
            status="success" if ok else "warning",
            human_message="Memory key removed" if ok else "Memory key not found",
            structured_payload={"memory_key": key},
        )

    def _memory_pin(self, req: CommandRequest) -> CommandResult:
        key = str(req.entities.get("memory_key") or "")
        if not key:
            return CommandResult("memory.pin", "warning", "memory_key is required")
        ok = self.memory.pin(req.context.user_id, key)
        return CommandResult(
            event_type="memory.pin",
            status="success" if ok else "warning",
            human_message="Memory key pinned" if ok else "Memory key not found",
            structured_payload={"memory_key": key},
        )

    def _deployments_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.deployments_list(app_name, region)
        return CommandResult("deployments.list", "success", "Deployment list loaded", payload)

    def _deployments_details(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        deployment_id = str(req.entities.get("deployment_id") or "")
        if not deployment_id:
            return CommandResult("deployments.details", "warning", "deployment_id is required")
        payload = self.gateway.deployment_details(app_name, region, deployment_id)
        return CommandResult("deployments.details", "success", "Deployment details loaded", payload)

    def _deployments_output(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        deployment_id = str(req.entities.get("deployment_id") or "")
        if not deployment_id:
            return CommandResult("deployments.output", "warning", "deployment_id is required")
        payload = self.gateway.deployment_output(app_name, region, deployment_id)
        return CommandResult("deployments.output", "success", "Deployment output loaded", payload)

    def _deployments_cache_reset(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.deployment_cache_reset(app_name, region)
        return CommandResult("deployments.cache_reset", "success", "Deployment cache reset requested", payload)

    def _autoscalers_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.autoscalers_list(app_name, region)
        return CommandResult("autoscalers.list", "success", "Autoscalers loaded", payload)

    def _autoscalers_create(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = {
            "autoscaler": {
                "container_type": req.entities.get("container_type"),
                "min_containers": int(req.entities.get("min_containers")),
                "max_containers": int(req.entities.get("max_containers")),
                "metric": req.entities.get("metric"),
                "target": float(req.entities.get("target")),
                "disabled": bool(req.entities.get("disabled", False)),
            }
        }
        result = self.gateway.autoscalers_create(app_name, region, payload)
        return CommandResult("autoscalers.create", "success", "Autoscaler created", result, risk_level="high")

    def _autoscalers_update(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        autoscaler_id = str(req.entities.get("autoscaler_id") or "")
        patch = {}
        for key in ("min_containers", "max_containers", "metric", "target", "disabled"):
            if key in req.entities:
                patch[key] = req.entities.get(key)
        payload = {"autoscaler": patch}
        result = self.gateway.autoscalers_update(app_name, region, autoscaler_id, payload)
        return CommandResult("autoscalers.update", "success", "Autoscaler updated", result, risk_level="high")

    def _autoscalers_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        autoscaler_id = str(req.entities.get("autoscaler_id") or "")
        payload = self.gateway.autoscalers_delete(app_name, region, autoscaler_id)
        return CommandResult("autoscalers.delete", "success", f"Autoscaler {autoscaler_id} delete requested", payload, risk_level="high")

    def _events_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.events_list(app_name, region)
        return CommandResult("events.list", "success", "Events loaded", payload)

    def _domains_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.domains_list(app_name, region)
        return CommandResult("domains.list", "success", "Domains loaded", payload)

    def _domains_create(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        domain_name = str(req.entities.get("domain") or "")
        domain_payload: Dict[str, Any] = {"name": domain_name}
        if "canonical" in req.entities:
            domain_payload["canonical"] = bool(req.entities.get("canonical"))
        if "letsencrypt_enabled" in req.entities:
            domain_payload["letsencrypt_enabled"] = bool(req.entities.get("letsencrypt_enabled"))
        payload = self.gateway.domains_create(app_name, region, {"domain": domain_payload})
        return CommandResult("domains.create", "success", f"Domain {domain_name} creation requested", payload, risk_level="high")

    def _domains_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        domain = str(req.entities.get("domain") or "")
        payload = self.gateway.domains_delete(app_name, region, domain)
        return CommandResult("domains.delete", "success", f"Domain {domain} delete requested", payload, risk_level="high")

    def _collaborators_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.collaborators_list(app_name, region)
        return CommandResult("collaborators.list", "success", "Collaborators loaded", payload)

    def _collaborators_invite(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = {
            "collaborator": {
                "email": req.entities.get("email"),
                "is_limited": bool(req.entities.get("is_limited", True)),
            }
        }
        result = self.gateway.collaborators_invite(app_name, region, payload)
        return CommandResult("collaborators.invite", "success", "Collaborator invitation requested", result, risk_level="high")

    def _collaborators_update_role(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        collaborator_id = str(req.entities.get("collaborator_id") or "")
        is_limited = self._as_bool(req.entities.get("is_limited"))
        if is_limited is None:
            return CommandResult("collaborators.update_role", "warning", "is_limited must be a boolean")
        payload = {"collaborator": {"is_limited": is_limited}}
        result = self.gateway.collaborators_update(app_name, region, collaborator_id, payload)
        return CommandResult("collaborators.update_role", "success", "Collaborator role updated", result, risk_level="high")

    def _collaborators_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        collaborator_id = str(req.entities.get("collaborator_id") or "")
        payload = self.gateway.collaborators_delete(app_name, region, collaborator_id)
        return CommandResult(
            "collaborators.delete",
            "success",
            f"Collaborator {collaborator_id} removal requested",
            payload,
            risk_level="high",
        )

    def _log_drains_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.log_drains_list(app_name, region)
        return CommandResult("log_drains.list", "success", "Log drains loaded", payload)

    def _log_drains_create(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        drain_payload = {
            "drain": {
                "type": req.entities.get("drain_type"),
                "token": req.entities.get("drain_token"),
                "host": req.entities.get("drain_host"),
                "url": req.entities.get("drain_url"),
            }
        }
        payload = self.gateway.log_drains_create(app_name, region, drain_payload)
        return CommandResult("log_drains.create", "success", "Log drain creation requested", payload, risk_level="high")

    def _log_drains_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        drain_id = str(req.entities.get("drain_id") or "")
        payload = self.gateway.log_drains_delete(app_name, region, drain_id)
        return CommandResult("log_drains.delete", "success", f"Log drain {drain_id} delete requested", payload, risk_level="high")

    def _notifiers_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.notifiers_list(app_name, region)
        return CommandResult("notifiers.list", "success", "Notifiers loaded", payload)

    def _notifiers_create(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = {
            "notifier": {
                "name": req.entities.get("notifier_name"),
                "platform_id": req.entities.get("platform_id"),
                "type_data": req.entities.get("type_data", {}),
            }
        }
        result = self.gateway.notifiers_create(app_name, region, payload)
        return CommandResult("notifiers.create", "success", "Notifier creation requested", result, risk_level="high")

    def _notifiers_update(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        notifier_id = str(req.entities.get("notifier_id") or "")
        patch = dict(req.entities.get("notifier_patch") or {})
        payload = {"notifier": patch}
        result = self.gateway.notifiers_update(app_name, region, notifier_id, payload)
        return CommandResult("notifiers.update", "success", "Notifier updated", result, risk_level="high")

    def _notifiers_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        notifier_id = str(req.entities.get("notifier_id") or "")
        payload = self.gateway.notifiers_delete(app_name, region, notifier_id)
        return CommandResult("notifiers.delete", "success", f"Notifier {notifier_id} delete requested", payload, risk_level="high")

    def _one_off_run(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        command = str(req.entities.get("command") or "")
        payload = self.gateway.one_off_run(
            app_name,
            region,
            command,
            size=req.entities.get("size"),
            detached=req.entities.get("detached"),
            env=req.entities.get("env"),
        )
        return CommandResult("one_off.run", "success", "One-off execution requested", payload)

    def _containers_stop(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        container_id = str(req.entities.get("container_id") or "")
        payload = self.gateway.containers_stop(app_name, region, container_id)
        return CommandResult("containers.stop", "success", f"Container {container_id} stop requested", payload, risk_level="high")

    def _containers_signal(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        container_id = str(req.entities.get("container_id") or "")
        signal = str(req.entities.get("signal") or "")
        payload = self.gateway.containers_signal(app_name, region, container_id, signal)
        return CommandResult("containers.signal", "success", f"Signal {signal} sent to {container_id}", payload, risk_level="high")

    def _projects_list(self, req: CommandRequest) -> CommandResult:
        region = str(req.entities.get("region") or req.context.region_scope or "")
        if not region:
            return CommandResult("projects.list", "warning", "region is required")
        payload = self.gateway.projects_list(region)
        return CommandResult("projects.list", "success", "Projects loaded", payload)

    def _confirm(self, req: CommandRequest) -> CommandResult:
        token = str(req.entities.get("confirm_token") or "")
        if not token:
            return CommandResult("confirm", "warning", "confirm_token is required")

        approved = self.memory.consume_confirmation_token(req.context.session_id, token)
        if not approved:
            return CommandResult("confirm", "warning", "Invalid or expired confirmation token")

        nested_entities = dict(approved.get("payload", {}).get("entities", {}))
        nested_command = str(approved.get("command", ""))
        nested_entities["confirm_token"] = token
        return self.execute(nested_command, nested_entities, str(approved.get("payload", {}).get("raw_text", "")), req.context)
