"""
Addon command handlers.

This module contains all command handlers related to addon management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "addons.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class AddonListHandler(BaseCommandHandler):
    """Handler for listing addons."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.addons_list(app_name, region)
        return CommandResult("addons.list", "success", "Addons loaded", payload)


@handler(
    "addons.add",
    HandlerConfig(
        required_entities=("addon_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AddonAddHandler(BaseCommandHandler):
    """Handler for adding an addon."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.addons_add(
            app_name,
            region,
            addon_id=str(request.entities.get("addon_id")),
            plan=str(request.entities.get("addon_plan") or ""),
            options=request.entities.get("addon_options") if isinstance(request.entities.get("addon_options"), dict) else None,
        )
        return self._with_mutation_preview(
            request,
            CommandResult("addons.add", "success", "Addon provisioning requested", payload),
        )


@handler(
    "addons.remove",
    HandlerConfig(
        required_entities=("addon_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class AddonRemoveHandler(BaseCommandHandler):
    """Handler for removing an addon."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.addons_remove(app_name, region, str(request.entities.get("addon_id")))
        return self._with_mutation_preview(
            request,
            CommandResult("addons.remove", "success", "Addon removal requested", payload, risk_level="high"),
        )
