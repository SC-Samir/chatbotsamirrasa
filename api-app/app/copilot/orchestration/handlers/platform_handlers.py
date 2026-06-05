"""
Platform command handlers.

This module contains command handlers for platform-level operations.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "scalingo.status",
    HandlerConfig(
        required_entities=(),
        requires_app_region=False,
        is_mutating=False,
    ),
)
class ScalingoStatusHandler(BaseCommandHandler):
    """Handler for getting Scalingo platform status."""

    def handle(self, request: CommandRequest) -> CommandResult:
        payload = self.gateway.scalingo_status()
        return CommandResult("scalingo.status", "success", "Scalingo platform status loaded", payload)


@handler(
    "batch.execute",
    HandlerConfig(
        required_entities=("commands",),
        requires_app_region=False,
        is_mutating=True,
    ),
)
class BatchExecuteHandler(BaseCommandHandler):
    """Handler for executing multiple commands in batch."""

    def handle(self, request: CommandRequest) -> CommandResult:
        commands = request.entities.get("commands", [])
        
        if not isinstance(commands, list):
            return CommandResult(
                "batch.execute",
                "error",
                "commands must be a list of command objects",
                {"error": "Invalid commands format"},
            )
        
        if len(commands) == 0:
            return CommandResult(
                "batch.execute",
                "warning",
                "No commands to execute",
                {"batch_results": [], "total": 0, "successful": 0},
            )
        
        if len(commands) > 10:  # Limit batch size
            return CommandResult(
                "batch.execute",
                "error",
                "Maximum batch size is 10 commands",
                {"error": "Batch size exceeded", "max_size": 10},
            )
        
        payload = self.gateway.batch_execute(commands)
        return CommandResult("batch.execute", "success", "Batch execution completed", payload)
