"""
App command handlers.

This module contains all command handlers related to application management.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "apps.list",
    HandlerConfig(
        required_entities=("region",),
        requires_app_region=False,
        is_mutating=False,
    ),
)
class AppListHandler(BaseCommandHandler):
    """Handler for listing applications."""

    def handle(self, request: CommandRequest) -> CommandResult:
        region = str(request.entities.get("region") or request.context.region_scope or "")
        payload = self.gateway.apps_list(region)
        return CommandResult("apps.list", "success", "Applications loaded", payload)


@handler(
    "apps.get",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class AppGetHandler(BaseCommandHandler):
    """Handler for getting application details."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.apps_get(app_name, region)
        return CommandResult("apps.get", "success", "Application loaded", payload)


@handler(
    "apps.create",
    HandlerConfig(
        required_entities=("app_name", "region"),
        idempotent=False,
        is_mutating=True,
    ),
)
class AppCreateHandler(BaseCommandHandler):
    """Handler for creating an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        payload = self.gateway.apps_create(
            str(request.entities.get("app_name")),
            str(request.entities.get("region")),
        )
        return self._with_mutation_preview(
            request,
            CommandResult("apps.create", "success", "Application creation requested", payload),
        )


@handler(
    "apps.delete",
    HandlerConfig(
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class AppDeleteHandler(BaseCommandHandler):
    """Handler for deleting an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.apps_delete(app_name, region)
        if payload.get("accepted") is False:
            return CommandResult(
                "apps.delete",
                "error",
                "Application deletion failed or was rejected by Scalingo API",
                payload,
                risk_level="high",
            )
        return self._with_mutation_preview(
            request,
            CommandResult("apps.delete", "success", "Application deletion requested", payload, risk_level="high"),
        )


@handler(
    "apps.rename",
    HandlerConfig(
        required_entities=("new_name",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AppRenameHandler(BaseCommandHandler):
    """Handler for renaming an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        new_name = str(request.entities.get("new_name") or "")
        payload = self.gateway.apps_update(app_name, region, {"name": new_name})
        return self._with_mutation_preview(
            request,
            CommandResult("apps.rename", "success", "Application rename requested", payload),
        )


@handler(
    "apps.restart",
    HandlerConfig(
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AppRestartHandler(BaseCommandHandler):
    """Handler for restarting an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.apps_restart(
            app_name,
            region,
            scope=request.entities.get("scope"),
        )
        return self._with_mutation_preview(
            request,
            CommandResult("apps.restart", "success", "Application restart requested", payload),
        )


@handler(
    "apps.set_force_https",
    HandlerConfig(
        required_entities=("enabled",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AppSetForceHttpsHandler(BaseCommandHandler):
    """Handler for setting force_https on an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        enabled = self._as_bool(request.entities.get("enabled"))
        if enabled is None:
            return CommandResult("apps.update", "warning", "enabled must be a boolean")
        payload = self.gateway.apps_update(app_name, region, {"force_https": enabled})
        return self._with_mutation_preview(
            request,
            CommandResult("apps.update", "success", "Application force_https updated", payload),
        )


@handler(
    "apps.set_router_logs",
    HandlerConfig(
        required_entities=("enabled",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AppSetRouterLogsHandler(BaseCommandHandler):
    """Handler for setting router_logs on an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        enabled = self._as_bool(request.entities.get("enabled"))
        if enabled is None:
            return CommandResult("apps.update", "warning", "enabled must be a boolean")
        payload = self.gateway.apps_update(app_name, region, {"router_logs": enabled})
        return self._with_mutation_preview(
            request,
            CommandResult("apps.update", "success", "Application router_logs updated", payload),
        )


@handler(
    "apps.set_sticky_session",
    HandlerConfig(
        required_entities=("enabled",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AppSetStickySessionHandler(BaseCommandHandler):
    """Handler for setting sticky_session on an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        enabled = self._as_bool(request.entities.get("enabled"))
        if enabled is None:
            return CommandResult("apps.update", "warning", "enabled must be a boolean")
        payload = self.gateway.apps_update(app_name, region, {"sticky_session": enabled})
        return self._with_mutation_preview(
            request,
            CommandResult("apps.update", "success", "Application sticky_session updated", payload),
        )


@handler(
    "apps.change_project",
    HandlerConfig(
        required_entities=("project_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class AppChangeProjectHandler(BaseCommandHandler):
    """Handler for changing the project of an application."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        project_id = str(request.entities.get("project_id") or "")
        payload = self.gateway.apps_update(app_name, region, {"project_id": project_id})
        return self._with_mutation_preview(
            request,
            CommandResult("apps.change_project", "success", "Application project updated", payload),
        )
