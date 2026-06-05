"""
Confirmation command handler.

This module contains the handler for confirming destructive actions.
"""
from __future__ import annotations

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "confirm",
    HandlerConfig(
        required_entities=("confirm_token",),
        idempotent=False,
    ),
)
class ConfirmHandler(BaseCommandHandler):
    """Handler for confirming destructive actions."""

    def handle(self, request: CommandRequest) -> CommandResult:
        token = str(request.entities.get("confirm_token") or "")
        if not token:
            return CommandResult("confirm", "warning", "confirm_token is required")

        approved = self.memory.consume_confirmation_token(request.context.session_id, token)
        if not approved:
            return CommandResult("confirm", "warning", "Invalid or expired confirmation token")

        nested_entities = dict(approved.get("payload", {}).get("entities", {}))
        nested_command = str(approved.get("command", ""))
        nested_entities["confirm_token"] = token
        
        # Create a new engine instance to execute the nested command
        from app.copilot.orchestration.engine import CommandEngine
        
        # Create a temporary engine to execute the command
        temp_engine = CommandEngine(self.gateway, self.memory)
        return temp_engine.execute(
            nested_command,
            nested_entities,
            str(approved.get("payload", {}).get("raw_text", "")),
            request.context,
        )
