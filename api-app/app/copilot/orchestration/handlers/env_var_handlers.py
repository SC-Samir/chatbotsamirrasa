"""
Environment variable command handlers.

This module contains all command handlers related to environment variable management.
"""
from __future__ import annotations

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "env_vars.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class EnvVarListHandler(BaseCommandHandler):
    """Handler for listing environment variables."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.env_vars_list(app_name, region, aliases=bool(request.entities.get("aliases", True)))
        return CommandResult("env_vars.list", "success", "Environment variables loaded", payload)


@handler(
    "env_vars.set",
    HandlerConfig(
        required_entities=("env_name", "env_value"),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class EnvVarSetHandler(BaseCommandHandler):
    """Handler for setting an environment variable."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.env_vars_set(app_name, region, str(request.entities.get("env_name")), str(request.entities.get("env_value")))
        return self._with_mutation_preview(
            request,
            CommandResult("env_vars.set", "success", "Environment variable set", payload),
        )


@handler(
    "env_vars.unset",
    HandlerConfig(
        required_entities=("env_name",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class EnvVarUnsetHandler(BaseCommandHandler):
    """Handler for unsetting an environment variable."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.env_vars_unset(app_name, region, str(request.entities.get("env_name")))
        return self._with_mutation_preview(
            request,
            CommandResult("env_vars.unset", "success", "Environment variable unset requested", payload, risk_level="high"),
        )
