"""
Project command handlers.

This module contains all command handlers related to project management.
"""
from __future__ import annotations

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "projects.list",
    HandlerConfig(
        required_entities=("region",),
        requires_app_region=False,
        is_mutating=False,
    ),
)
class ProjectListHandler(BaseCommandHandler):
    """Handler for listing projects."""

    def handle(self, request: CommandRequest) -> CommandResult:
        region = str(request.entities.get("region") or request.context.region_scope or "")
        payload = self.gateway.projects_list(region)
        return CommandResult("projects.list", "success", "Projects loaded", payload)
