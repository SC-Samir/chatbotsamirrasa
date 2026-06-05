"""
Notifier command handlers.

This module contains all command handlers related to notifier management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "notifiers.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class NotifierListHandler(BaseCommandHandler):
    """Handler for listing notifiers."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.notifiers_list(app_name, region)
        return CommandResult("notifiers.list", "success", "Notifiers loaded", payload)


@handler(
    "notifiers.create",
    HandlerConfig(
        required_entities=("notifier_name", "platform_id"),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class NotifierCreateHandler(BaseCommandHandler):
    """Handler for creating a notifier."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = {
            "notifier": {
                "name": request.entities.get("notifier_name"),
                "platform_id": request.entities.get("platform_id"),
                "type_data": request.entities.get("type_data", {}),
            }
        }
        result = self.gateway.notifiers_create(app_name, region, payload)
        return self._with_mutation_preview(
            request,
            CommandResult("notifiers.create", "success", "Notifier creation requested", result),
        )


@handler(
    "notifiers.update",
    HandlerConfig(
        required_entities=("notifier_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class NotifierUpdateHandler(BaseCommandHandler):
    """Handler for updating a notifier."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        notifier_id = str(request.entities.get("notifier_id") or "")
        patch = dict(request.entities.get("notifier_patch") or {})
        payload = {"notifier": patch}
        result = self.gateway.notifiers_update(app_name, region, notifier_id, payload)
        return self._with_mutation_preview(
            request,
            CommandResult("notifiers.update", "success", "Notifier updated", result),
        )


@handler(
    "notifiers.delete",
    HandlerConfig(
        required_entities=("notifier_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class NotifierDeleteHandler(BaseCommandHandler):
    """Handler for deleting a notifier."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        notifier_id = str(request.entities.get("notifier_id") or "")
        payload = self.gateway.notifiers_delete(app_name, region, notifier_id)
        return self._with_mutation_preview(
            request,
            CommandResult("notifiers.delete", "success", f"Notifier {notifier_id} delete requested", payload, risk_level="high"),
        )
