"""
Region command handlers.

This module contains command handlers for region-related operations.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "regions.list",
    HandlerConfig(
        required_entities=(),
        requires_app_region=False,
        is_mutating=False,
    ),
)
class RegionsListHandler(BaseCommandHandler):
    """Handler for listing all available regions."""

    def handle(self, request: CommandRequest) -> CommandResult:
        payload = self.gateway.regions_list()
        return CommandResult("regions.list", "success", "Available regions loaded", payload)
