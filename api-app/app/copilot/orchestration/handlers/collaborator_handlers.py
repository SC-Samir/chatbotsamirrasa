"""
Collaborator command handlers.

This module contains all command handlers related to collaborator management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "collaborators.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class CollaboratorListHandler(BaseCommandHandler):
    """Handler for listing collaborators."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.collaborators_list(app_name, region)
        return CommandResult("collaborators.list", "success", "Collaborators loaded", payload)


@handler(
    "collaborators.invite",
    HandlerConfig(
        required_entities=("email",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class CollaboratorInviteHandler(BaseCommandHandler):
    """Handler for inviting a collaborator."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = {
            "collaborator": {
                "email": request.entities.get("email"),
                "is_limited": bool(request.entities.get("is_limited", True)),
            }
        }
        result = self.gateway.collaborators_invite(app_name, region, payload)
        return self._with_mutation_preview(
            request,
            CommandResult("collaborators.invite", "success", "Collaborator invitation requested", result),
        )


@handler(
    "collaborators.update_role",
    HandlerConfig(
        required_entities=("collaborator_id", "is_limited"),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class CollaboratorUpdateRoleHandler(BaseCommandHandler):
    """Handler for updating collaborator role."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        collaborator_id = str(request.entities.get("collaborator_id") or "")
        is_limited = self._as_bool(request.entities.get("is_limited"))
        if is_limited is None:
            return CommandResult("collaborators.update_role", "warning", "is_limited must be a boolean")
        payload = {"collaborator": {"is_limited": is_limited}}
        result = self.gateway.collaborators_update(app_name, region, collaborator_id, payload)
        return self._with_mutation_preview(
            request,
            CommandResult("collaborators.update_role", "success", "Collaborator role updated", result),
        )


@handler(
    "collaborators.delete",
    HandlerConfig(
        required_entities=("collaborator_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class CollaboratorDeleteHandler(BaseCommandHandler):
    """Handler for deleting a collaborator."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        collaborator_id = str(request.entities.get("collaborator_id") or "")
        payload = self.gateway.collaborators_delete(app_name, region, collaborator_id)
        return self._with_mutation_preview(
            request,
            CommandResult("collaborators.delete", "success", f"Collaborator {collaborator_id} removal requested", payload, risk_level="high"),
        )
