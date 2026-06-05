"""
Autoscaler command handlers.

This module contains all command handlers related to autoscaler management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "autoscalers.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class AutoscalerListHandler(BaseCommandHandler):
    """Handler for listing autoscalers."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.autoscalers_list(app_name, region)
        return CommandResult("autoscalers.list", "success", "Autoscalers loaded", payload)


@handler(
    "autoscalers.create",
    HandlerConfig(
        required_entities=("container_type", "min_containers", "max_containers", "metric", "target"),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AutoscalerCreateHandler(BaseCommandHandler):
    """Handler for creating an autoscaler."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = {
            "autoscaler": {
                "container_type": request.entities.get("container_type"),
                "min_containers": int(request.entities.get("min_containers")),
                "max_containers": int(request.entities.get("max_containers")),
                "metric": request.entities.get("metric"),
                "target": float(request.entities.get("target")),
                "disabled": bool(request.entities.get("disabled", False)),
            }
        }
        result = self.gateway.autoscalers_create(app_name, region, payload)
        return self._with_mutation_preview(
            request,
            CommandResult("autoscalers.create", "success", "Autoscaler created", result),
        )


@handler(
    "autoscalers.update",
    HandlerConfig(
        required_entities=("autoscaler_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AutoscalerUpdateHandler(BaseCommandHandler):
    """Handler for updating an autoscaler."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        autoscaler_id = str(request.entities.get("autoscaler_id") or "")
        patch: Dict[str, Any] = {}
        for key in ("min_containers", "max_containers", "metric", "target", "disabled"):
            if key in request.entities:
                patch[key] = request.entities.get(key)
        payload = {"autoscaler": patch}
        result = self.gateway.autoscalers_update(app_name, region, autoscaler_id, payload)
        return self._with_mutation_preview(
            request,
            CommandResult("autoscalers.update", "success", "Autoscaler updated", result),
        )


@handler(
    "autoscalers.delete",
    HandlerConfig(
        required_entities=("autoscaler_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class AutoscalerDeleteHandler(BaseCommandHandler):
    """Handler for deleting an autoscaler."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        autoscaler_id = str(request.entities.get("autoscaler_id") or "")
        payload = self.gateway.autoscalers_delete(app_name, region, autoscaler_id)
        return self._with_mutation_preview(
            request,
            CommandResult("autoscalers.delete", "success", f"Autoscaler {autoscaler_id} delete requested", payload, risk_level="high"),
        )
