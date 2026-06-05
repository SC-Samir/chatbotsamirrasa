"""
Event command handlers.

This module contains all command handlers related to event management.
"""
from __future__ import annotations

from typing import Any

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "events.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class EventListHandler(BaseCommandHandler):
    """Handler for listing events."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.events_list(
            app_name,
            region,
            page=request.entities.get("page"),
            per_page=request.entities.get("per_page"),
            event_type=request.entities.get("event_type"),
        )
        return CommandResult("events.list", "success", "Events loaded", payload)
