"""
Deployment command handlers.

This module contains all command handlers related to deployment management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "deployments.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class DeploymentListHandler(BaseCommandHandler):
    """Handler for listing deployments."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.deployments_list(app_name, region)
        return CommandResult("deployments.list", "success", "Deployment list loaded", payload)


@handler(
    "deployments.details",
    HandlerConfig(
        required_entities=("deployment_id",),
        requires_app_region=True,
        is_mutating=False,
    ),
)
class DeploymentDetailsHandler(BaseCommandHandler):
    """Handler for getting deployment details."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        deployment_id = str(request.entities.get("deployment_id") or "")
        payload = self.gateway.deployment_details(app_name, region, deployment_id)
        return CommandResult("deployments.details", "success", "Deployment details loaded", payload)


@handler(
    "deployments.output",
    HandlerConfig(
        required_entities=("deployment_id",),
        requires_app_region=True,
        is_mutating=False,
    ),
)
class DeploymentOutputHandler(BaseCommandHandler):
    """Handler for getting deployment output."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        deployment_id = str(request.entities.get("deployment_id") or "")
        payload = self.gateway.deployment_output(app_name, region, deployment_id)
        return CommandResult("deployments.output", "success", "Deployment output loaded", payload)


@handler(
    "deployments.create",
    HandlerConfig(
        required_entities=("github_repo",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class DeploymentCreateHandler(BaseCommandHandler):
    """Handler for creating a deployment."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.deployments_create(
            app_name,
            region,
            source_url=str(request.entities.get("source_url") or ""),
            github_repo=str(request.entities.get("github_repo") or ""),
            git_ref=str(request.entities.get("git_ref") or "main"),
        )
        return self._with_mutation_preview(
            request,
            CommandResult("deployments.create", "success", "Deployment requested", payload),
        )


@handler(
    "deployments.cache_reset",
    HandlerConfig(
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class DeploymentCacheResetHandler(BaseCommandHandler):
    """Handler for resetting deployment cache."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.deployment_cache_reset(app_name, region)
        return self._with_mutation_preview(
            request,
            CommandResult(
                "deployments.cache_reset",
                "success",
                "Deployment cache reset requested",
                payload,
                risk_level="high",
            ),
        )


@handler(
    "deployments.rollback",
    HandlerConfig(
        required_entities=("release_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class DeploymentRollbackHandler(BaseCommandHandler):
    """Handler for rolling back a deployment."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.deployments_rollback(
            app_name,
            region,
            str(request.entities.get("release_id")),
        )
        return self._with_mutation_preview(
            request,
            CommandResult("deployments.rollback", "success", "Rollback requested", payload),
        )
