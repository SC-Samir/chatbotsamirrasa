from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from app.copilot.contracts import CommandContext, CommandRequest, CommandResult
from app.copilot.memory.service import MemoryService
from app.copilot.scalingo_ops.gateway import ScalingoOpsGateway

Handler = Callable[[CommandRequest], CommandResult]


@dataclass(frozen=True)
class CommandMetadata:
    required_entities: Tuple[str, ...] = ()
    idempotent: bool = True
    requires_app_region: bool = False
    is_mutating: bool = False
    is_destructive: bool = False


class CommandEngine:
    def __init__(self, gateway: ScalingoOpsGateway, memory: MemoryService):
        self.gateway = gateway
        self.memory = memory
        self.registry: Dict[str, Handler] = {
            "apps.list": self._apps_list,
            "apps.get": self._apps_get,
            "apps.create": self._apps_create,
            "apps.delete": self._apps_delete,
            "apps.rename": self._apps_rename,
            "apps.restart": self._apps_restart,
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
            "deployments.create": self._deployments_create,
            "deployments.cache_reset": self._deployments_cache_reset,
            "deployments.rollback": self._deployments_rollback,
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
            "containers.list": self._containers_list,
            "containers.scale": self._containers_scale,
            "containers.stop": self._containers_stop,
            "containers.signal": self._containers_signal,
            "projects.list": self._projects_list,
            "env_vars.list": self._env_vars_list,
            "env_vars.set": self._env_vars_set,
            "env_vars.unset": self._env_vars_unset,
            "addons.list": self._addons_list,
            "addons.add": self._addons_add,
            "addons.remove": self._addons_remove,
            "confirm": self._confirm,
        }
        self.metadata: Dict[str, CommandMetadata] = {
            "apps.list": CommandMetadata(required_entities=("region",)),
            "apps.get": CommandMetadata(requires_app_region=True),
            "apps.create": CommandMetadata(required_entities=("app_name", "region"), idempotent=False, is_mutating=True),
            "apps.delete": CommandMetadata(requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "apps.rename": CommandMetadata(required_entities=("new_name",), requires_app_region=True, idempotent=False, is_mutating=True),
            "apps.restart": CommandMetadata(requires_app_region=True, idempotent=False, is_mutating=True),
            "apps.set_force_https": CommandMetadata(required_entities=("enabled",), requires_app_region=True, idempotent=False, is_mutating=True),
            "apps.set_router_logs": CommandMetadata(required_entities=("enabled",), requires_app_region=True, idempotent=False, is_mutating=True),
            "apps.set_sticky_session": CommandMetadata(required_entities=("enabled",), requires_app_region=True, idempotent=False, is_mutating=True),
            "apps.change_project": CommandMetadata(required_entities=("project_id",), requires_app_region=True, idempotent=False, is_mutating=True),
            "memory.show": CommandMetadata(),
            "memory.forget": CommandMetadata(required_entities=("memory_key",), idempotent=False, is_mutating=True),
            "memory.pin": CommandMetadata(required_entities=("memory_key",), idempotent=False, is_mutating=True),
            "deployments.list": CommandMetadata(requires_app_region=True),
            "deployments.details": CommandMetadata(required_entities=("deployment_id",), requires_app_region=True),
            "deployments.output": CommandMetadata(required_entities=("deployment_id",), requires_app_region=True),
            "deployments.create": CommandMetadata(required_entities=("github_repo",), requires_app_region=True, idempotent=False, is_mutating=True),
            "deployments.cache_reset": CommandMetadata(requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "deployments.rollback": CommandMetadata(required_entities=("release_id",), requires_app_region=True, idempotent=False, is_mutating=True),
            "autoscalers.list": CommandMetadata(requires_app_region=True),
            "autoscalers.create": CommandMetadata(required_entities=("container_type", "min_containers", "max_containers", "metric", "target"), requires_app_region=True, idempotent=False, is_mutating=True),
            "autoscalers.update": CommandMetadata(required_entities=("autoscaler_id",), requires_app_region=True, idempotent=False, is_mutating=True),
            "autoscalers.delete": CommandMetadata(required_entities=("autoscaler_id",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "events.list": CommandMetadata(requires_app_region=True),
            "domains.list": CommandMetadata(requires_app_region=True),
            "domains.create": CommandMetadata(required_entities=("domain",), requires_app_region=True, idempotent=False, is_mutating=True),
            "domains.delete": CommandMetadata(required_entities=("domain",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "collaborators.list": CommandMetadata(requires_app_region=True),
            "collaborators.invite": CommandMetadata(required_entities=("email",), requires_app_region=True, idempotent=False, is_mutating=True),
            "collaborators.update_role": CommandMetadata(required_entities=("collaborator_id", "is_limited"), requires_app_region=True, idempotent=False, is_mutating=True),
            "collaborators.delete": CommandMetadata(required_entities=("collaborator_id",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "log_drains.list": CommandMetadata(requires_app_region=True),
            "log_drains.create": CommandMetadata(required_entities=("drain_type",), requires_app_region=True, idempotent=False, is_mutating=True),
            "log_drains.delete": CommandMetadata(required_entities=("drain_id",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "notifiers.list": CommandMetadata(requires_app_region=True),
            "notifiers.create": CommandMetadata(required_entities=("notifier_name", "platform_id"), requires_app_region=True, idempotent=False, is_mutating=True),
            "notifiers.update": CommandMetadata(required_entities=("notifier_id",), requires_app_region=True, idempotent=False, is_mutating=True),
            "notifiers.delete": CommandMetadata(required_entities=("notifier_id",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "one_off.run": CommandMetadata(required_entities=("command",), requires_app_region=True, idempotent=False, is_mutating=True),
            "containers.list": CommandMetadata(requires_app_region=True),
            "containers.scale": CommandMetadata(required_entities=("container_type", "amount"), requires_app_region=True, idempotent=False, is_mutating=True),
            "containers.stop": CommandMetadata(required_entities=("container_id",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "containers.signal": CommandMetadata(required_entities=("container_id", "signal"), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "projects.list": CommandMetadata(required_entities=("region",)),
            "env_vars.list": CommandMetadata(requires_app_region=True),
            "env_vars.set": CommandMetadata(required_entities=("env_name", "env_value"), requires_app_region=True, idempotent=False, is_mutating=True),
            "env_vars.unset": CommandMetadata(required_entities=("env_name",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "addons.list": CommandMetadata(requires_app_region=True),
            "addons.add": CommandMetadata(required_entities=("addon_id",), requires_app_region=True, idempotent=False, is_mutating=True),
            "addons.remove": CommandMetadata(required_entities=("addon_id",), requires_app_region=True, idempotent=False, is_mutating=True, is_destructive=True),
            "confirm": CommandMetadata(required_entities=("confirm_token",), idempotent=False),
        }

    def is_destructive(self, command: str) -> bool:
        meta = self.metadata.get(command)
        return bool(meta and meta.is_destructive)

    def execute(self, command: str, entities: Dict[str, Any], raw_text: str, context: CommandContext) -> CommandResult:
        req = CommandRequest(command=command, entities=entities, raw_text=raw_text, context=context)
        meta = self.metadata.get(command)
        if meta and meta.is_destructive and not entities.get("confirm_token"):
            token = self.memory.issue_confirmation_token(
                session_id=context.session_id,
                command=command,
                payload={"entities": entities, "raw_text": raw_text},
            )
            return CommandResult(
                event_type="command.confirmation_required",
                status="requires_confirmation",
                human_message=f"Action preview: {self._preview_for(command, req)}. Destructive action, confirm with token {token}.",
                structured_payload={"confirm_token": token, "command": command, "preview": self._preview_for(command, req)},
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
                if not req.entities.get("app_name") and not req.context.app_scope:
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

    def _preview_for(self, command: str, req: CommandRequest) -> str:
        payload = {k: v for k, v in req.entities.items() if k not in {"confirm_token"}}
        return f"{command} with {payload}"

    def _with_mutation_preview(self, req: CommandRequest, result: CommandResult) -> CommandResult:
        preview = self._preview_for(req.command, req)
        return CommandResult(
            event_type=result.event_type,
            status=result.status,
            human_message=f"Action preview: {preview}. {result.human_message}",
            structured_payload={**result.structured_payload, "preview": preview},
            next_actions=result.next_actions,
            risk_level=result.risk_level,
            action_id=result.action_id,
        )

    def _apps_list(self, req: CommandRequest) -> CommandResult:
        region = str(req.entities.get("region") or req.context.region_scope or "")
        payload = self.gateway.apps_list(region)
        return CommandResult("apps.list", "success", "Applications loaded", payload)

    def _apps_get(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.apps_get(app_name, region)
        return CommandResult("apps.get", "success", "Application loaded", payload)

    def _apps_create(self, req: CommandRequest) -> CommandResult:
        payload = self.gateway.apps_create(str(req.entities.get("app_name")), str(req.entities.get("region")))
        return self._with_mutation_preview(req, CommandResult("apps.create", "success", "Application creation requested", payload))

    def _apps_restart(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.apps_restart(app_name, region, scope=req.entities.get("scope"))
        return self._with_mutation_preview(req, CommandResult("apps.restart", "success", "Application restart requested", payload))

    def _apps_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.apps_delete(app_name, region)
        if payload.get("accepted") is False:
            return CommandResult(
                "apps.delete",
                "error",
                "Application deletion failed or was rejected by Scalingo API",
                payload,
                risk_level="high",
            )
        return self._with_mutation_preview(req, CommandResult("apps.delete", "success", "Application deletion requested", payload, risk_level="high"))

    def _apps_rename(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        new_name = str(req.entities.get("new_name") or "")
        payload = self.gateway.apps_update(app_name, region, {"name": new_name})
        return self._with_mutation_preview(req, CommandResult("apps.rename", "success", "Application rename requested", payload))

    def _apps_update_field(self, req: CommandRequest, field_name: str, message: str) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        enabled = self._as_bool(req.entities.get("enabled"))
        if enabled is None:
            return CommandResult("apps.update", "warning", "enabled must be a boolean")
        payload = self.gateway.apps_update(app_name, region, {field_name: enabled})
        return self._with_mutation_preview(req, CommandResult("apps.update", "success", message, payload))

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
        return self._with_mutation_preview(req, CommandResult("apps.change_project", "success", "Application project updated", payload))

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
        ok = self.memory.forget(req.context.user_id, key)
        return self._with_mutation_preview(
            req,
            CommandResult(
                event_type="memory.forget",
                status="success" if ok else "warning",
                human_message="Memory key removed" if ok else "Memory key not found",
                structured_payload={"memory_key": key},
            ),
        )

    def _memory_pin(self, req: CommandRequest) -> CommandResult:
        key = str(req.entities.get("memory_key") or "")
        ok = self.memory.pin(req.context.user_id, key)
        return self._with_mutation_preview(
            req,
            CommandResult(
                event_type="memory.pin",
                status="success" if ok else "warning",
                human_message="Memory key pinned" if ok else "Memory key not found",
                structured_payload={"memory_key": key},
            ),
        )

    def _deployments_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.deployments_list(app_name, region)
        return CommandResult("deployments.list", "success", "Deployment list loaded", payload)

    def _deployments_details(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        deployment_id = str(req.entities.get("deployment_id") or "")
        payload = self.gateway.deployment_details(app_name, region, deployment_id)
        return CommandResult("deployments.details", "success", "Deployment details loaded", payload)

    def _deployments_output(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        deployment_id = str(req.entities.get("deployment_id") or "")
        payload = self.gateway.deployment_output(app_name, region, deployment_id)
        return CommandResult("deployments.output", "success", "Deployment output loaded", payload)

    def _deployments_create(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.deployments_create(
            app_name,
            region,
            source_url=str(req.entities.get("source_url") or ""),
            github_repo=str(req.entities.get("github_repo") or ""),
            git_ref=str(req.entities.get("git_ref") or "main"),
        )
        return self._with_mutation_preview(req, CommandResult("deployments.create", "success", "Deployment requested", payload))

    def _deployments_cache_reset(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.deployment_cache_reset(app_name, region)
        return self._with_mutation_preview(req, CommandResult("deployments.cache_reset", "success", "Deployment cache reset requested", payload, risk_level="high"))

    def _deployments_rollback(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.deployments_rollback(app_name, region, str(req.entities.get("release_id")))
        return self._with_mutation_preview(req, CommandResult("deployments.rollback", "success", "Rollback requested", payload))

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
        return self._with_mutation_preview(req, CommandResult("autoscalers.create", "success", "Autoscaler created", result))

    def _autoscalers_update(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        autoscaler_id = str(req.entities.get("autoscaler_id") or "")
        patch = {}
        for key in ("min_containers", "max_containers", "metric", "target", "disabled"):
            if key in req.entities:
                patch[key] = req.entities.get(key)
        payload = {"autoscaler": patch}
        result = self.gateway.autoscalers_update(app_name, region, autoscaler_id, payload)
        return self._with_mutation_preview(req, CommandResult("autoscalers.update", "success", "Autoscaler updated", result))

    def _autoscalers_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        autoscaler_id = str(req.entities.get("autoscaler_id") or "")
        payload = self.gateway.autoscalers_delete(app_name, region, autoscaler_id)
        return self._with_mutation_preview(req, CommandResult("autoscalers.delete", "success", f"Autoscaler {autoscaler_id} delete requested", payload, risk_level="high"))

    def _events_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.events_list(
            app_name,
            region,
            page=req.entities.get("page"),
            per_page=req.entities.get("per_page"),
            event_type=req.entities.get("event_type"),
        )
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
        return self._with_mutation_preview(req, CommandResult("domains.create", "success", f"Domain {domain_name} creation requested", payload))

    def _domains_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        domain = str(req.entities.get("domain") or "")
        payload = self.gateway.domains_delete(app_name, region, domain)
        return self._with_mutation_preview(req, CommandResult("domains.delete", "success", f"Domain {domain} delete requested", payload, risk_level="high"))

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
        return self._with_mutation_preview(req, CommandResult("collaborators.invite", "success", "Collaborator invitation requested", result))

    def _collaborators_update_role(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        collaborator_id = str(req.entities.get("collaborator_id") or "")
        is_limited = self._as_bool(req.entities.get("is_limited"))
        if is_limited is None:
            return CommandResult("collaborators.update_role", "warning", "is_limited must be a boolean")
        payload = {"collaborator": {"is_limited": is_limited}}
        result = self.gateway.collaborators_update(app_name, region, collaborator_id, payload)
        return self._with_mutation_preview(req, CommandResult("collaborators.update_role", "success", "Collaborator role updated", result))

    def _collaborators_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        collaborator_id = str(req.entities.get("collaborator_id") or "")
        payload = self.gateway.collaborators_delete(app_name, region, collaborator_id)
        return self._with_mutation_preview(req, CommandResult("collaborators.delete", "success", f"Collaborator {collaborator_id} removal requested", payload, risk_level="high"))

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
        return self._with_mutation_preview(req, CommandResult("log_drains.create", "success", "Log drain creation requested", payload))

    def _log_drains_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        drain_id = str(req.entities.get("drain_id") or "")
        payload = self.gateway.log_drains_delete(app_name, region, drain_id)
        return self._with_mutation_preview(req, CommandResult("log_drains.delete", "success", f"Log drain {drain_id} delete requested", payload, risk_level="high"))

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
        return self._with_mutation_preview(req, CommandResult("notifiers.create", "success", "Notifier creation requested", result))

    def _notifiers_update(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        notifier_id = str(req.entities.get("notifier_id") or "")
        patch = dict(req.entities.get("notifier_patch") or {})
        payload = {"notifier": patch}
        result = self.gateway.notifiers_update(app_name, region, notifier_id, payload)
        return self._with_mutation_preview(req, CommandResult("notifiers.update", "success", "Notifier updated", result))

    def _notifiers_delete(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        notifier_id = str(req.entities.get("notifier_id") or "")
        payload = self.gateway.notifiers_delete(app_name, region, notifier_id)
        return self._with_mutation_preview(req, CommandResult("notifiers.delete", "success", f"Notifier {notifier_id} delete requested", payload, risk_level="high"))

    def _one_off_run(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        command = str(req.entities.get("command") or "")
        payload = self.gateway.one_off_run(app_name, region, command, size=req.entities.get("size"), detached=req.entities.get("detached"), env=req.entities.get("env"))
        return self._with_mutation_preview(req, CommandResult("one_off.run", "success", "One-off execution requested", payload))

    def _containers_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.containers_list(app_name, region)
        return CommandResult("containers.list", "success", "Containers loaded", payload)

    def _containers_scale(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.containers_scale(
            app_name,
            region,
            container_type=str(req.entities.get("container_type")),
            amount=int(req.entities.get("amount")),
            size=req.entities.get("size"),
        )
        return self._with_mutation_preview(req, CommandResult("containers.scale", "success", "Container scaling requested", payload))

    def _containers_stop(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        container_id = str(req.entities.get("container_id") or "")
        payload = self.gateway.containers_stop(app_name, region, container_id)
        return self._with_mutation_preview(req, CommandResult("containers.stop", "success", f"Container {container_id} stop requested", payload, risk_level="high"))

    def _containers_signal(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        container_id = str(req.entities.get("container_id") or "")
        signal = str(req.entities.get("signal") or "")
        payload = self.gateway.containers_signal(app_name, region, container_id, signal)
        return self._with_mutation_preview(req, CommandResult("containers.signal", "success", f"Signal {signal} sent to {container_id}", payload, risk_level="high"))

    def _projects_list(self, req: CommandRequest) -> CommandResult:
        region = str(req.entities.get("region") or req.context.region_scope or "")
        payload = self.gateway.projects_list(region)
        return CommandResult("projects.list", "success", "Projects loaded", payload)

    def _env_vars_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.env_vars_list(app_name, region, aliases=bool(req.entities.get("aliases", True)))
        return CommandResult("env_vars.list", "success", "Environment variables loaded", payload)

    def _env_vars_set(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.env_vars_set(app_name, region, str(req.entities.get("env_name")), str(req.entities.get("env_value")))
        return self._with_mutation_preview(req, CommandResult("env_vars.set", "success", "Environment variable set", payload))

    def _env_vars_unset(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.env_vars_unset(app_name, region, str(req.entities.get("env_name")))
        return self._with_mutation_preview(req, CommandResult("env_vars.unset", "success", "Environment variable unset requested", payload, risk_level="high"))

    def _addons_list(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.addons_list(app_name, region)
        return CommandResult("addons.list", "success", "Addons loaded", payload)

    def _addons_add(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.addons_add(
            app_name,
            region,
            addon_id=str(req.entities.get("addon_id")),
            plan=str(req.entities.get("addon_plan") or ""),
            options=req.entities.get("addon_options") if isinstance(req.entities.get("addon_options"), dict) else None,
        )
        return self._with_mutation_preview(req, CommandResult("addons.add", "success", "Addon provisioning requested", payload))

    def _addons_remove(self, req: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(req)
        payload = self.gateway.addons_remove(app_name, region, str(req.entities.get("addon_id")))
        return self._with_mutation_preview(req, CommandResult("addons.remove", "success", "Addon removal requested", payload, risk_level="high"))

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
