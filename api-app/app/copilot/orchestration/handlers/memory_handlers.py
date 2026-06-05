"""
Memory command handlers.

This module contains all command handlers related to memory operations.
"""
from __future__ import annotations

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "memory.show",
    HandlerConfig(
        is_mutating=False,
    ),
)
class MemoryShowHandler(BaseCommandHandler):
    """Handler for showing memory snapshot."""

    def handle(self, request: CommandRequest) -> CommandResult:
        snap = self.memory.snapshot(request.context.user_id, request.context.session_id)
        return CommandResult(
            event_type="memory.snapshot",
            status="success",
            human_message="Current memory snapshot",
            structured_payload={"session": snap.session, "facts": snap.facts},
        )


@handler(
    "memory.forget",
    HandlerConfig(
        required_entities=("memory_key",),
        idempotent=False,
        is_mutating=True,
    ),
)
class MemoryForgetHandler(BaseCommandHandler):
    """Handler for forgetting a memory key."""

    def handle(self, request: CommandRequest) -> CommandResult:
        key = str(request.entities.get("memory_key") or "")
        ok = self.memory.forget(request.context.user_id, key)
        return self._with_mutation_preview(
            request,
            CommandResult(
                event_type="memory.forget",
                status="success" if ok else "warning",
                human_message="Memory key removed" if ok else "Memory key not found",
                structured_payload={"memory_key": key},
            ),
        )


@handler(
    "memory.pin",
    HandlerConfig(
        required_entities=("memory_key",),
        idempotent=False,
        is_mutating=True,
    ),
)
class MemoryPinHandler(BaseCommandHandler):
    """Handler for pinning a memory key."""

    def handle(self, request: CommandRequest) -> CommandResult:
        key = str(request.entities.get("memory_key") or "")
        ok = self.memory.pin(request.context.user_id, key)
        return self._with_mutation_preview(
            request,
            CommandResult(
                event_type="memory.pin",
                status="success" if ok else "warning",
                human_message="Memory key pinned" if ok else "Memory key not found",
                structured_payload={"memory_key": key},
            ),
        )
