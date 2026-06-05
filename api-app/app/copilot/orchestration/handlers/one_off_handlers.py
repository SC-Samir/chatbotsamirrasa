"""
One-off command handlers.

This module contains all command handlers related to one-off container execution.
"""
from __future__ import annotations

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "one_off.run",
    HandlerConfig(
        required_entities=("command",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class OneOffRunHandler(BaseCommandHandler):
    """Handler for running a one-off container."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        command = str(request.entities.get("command") or "")
        payload = self.gateway.one_off_run(
            app_name,
            region,
            command,
            size=request.entities.get("size"),
            detached=request.entities.get("detached"),
            env=request.entities.get("env"),
        )
        return self._with_mutation_preview(
            request,
            CommandResult("one_off.run", "success", "One-off execution requested", payload),
        )
