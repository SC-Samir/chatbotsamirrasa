"""
Log drain command handlers.

This module contains all command handlers related to log drain management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "log_drains.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class LogDrainListHandler(BaseCommandHandler):
    """Handler for listing log drains."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.log_drains_list(app_name, region)
        return CommandResult("log_drains.list", "success", "Log drains loaded", payload)


@handler(
    "log_drains.create",
    HandlerConfig(
        required_entities=("drain_type",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class LogDrainCreateHandler(BaseCommandHandler):
    """Handler for creating a log drain."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        drain_payload = {
            "drain": {
                "type": request.entities.get("drain_type"),
                "token": request.entities.get("drain_token"),
                "host": request.entities.get("drain_host"),
                "url": request.entities.get("drain_url"),
            }
        }
        payload = self.gateway.log_drains_create(app_name, region, drain_payload)
        return self._with_mutation_preview(
            request,
            CommandResult("log_drains.create", "success", "Log drain creation requested", payload),
        )


@handler(
    "log_drains.delete",
    HandlerConfig(
        required_entities=("drain_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class LogDrainDeleteHandler(BaseCommandHandler):
    """Handler for deleting a log drain."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        drain_id = str(request.entities.get("drain_id") or "")
        payload = self.gateway.log_drains_delete(app_name, region, drain_id)
        return self._with_mutation_preview(
            request,
            CommandResult("log_drains.delete", "success", f"Log drain {drain_id} delete requested", payload, risk_level="high"),
        )
