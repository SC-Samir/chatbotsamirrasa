"""
Container command handlers.

This module contains all command handlers related to container management.
"""
from __future__ import annotations

from typing import Any

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "containers.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class ContainerListHandler(BaseCommandHandler):
    """Handler for listing containers."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.containers_list(app_name, region)
        return CommandResult("containers.list", "success", "Containers loaded", payload)


@handler(
    "containers.scale",
    HandlerConfig(
        required_entities=("container_type", "amount"),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class ContainerScaleHandler(BaseCommandHandler):
    """Handler for scaling containers."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.containers_scale(
            app_name,
            region,
            container_type=str(request.entities.get("container_type")),
            amount=int(request.entities.get("amount")),
            size=request.entities.get("size"),
        )
        return self._with_mutation_preview(
            request,
            CommandResult("containers.scale", "success", "Container scaling requested", payload),
        )


@handler(
    "containers.stop",
    HandlerConfig(
        required_entities=("container_id",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class ContainerStopHandler(BaseCommandHandler):
    """Handler for stopping a container."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        container_id = str(request.entities.get("container_id") or "")
        payload = self.gateway.containers_stop(app_name, region, container_id)
        return self._with_mutation_preview(
            request,
            CommandResult("containers.stop", "success", f"Container {container_id} stop requested", payload, risk_level="high"),
        )


@handler(
    "containers.signal",
    HandlerConfig(
        required_entities=("container_id", "signal"),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class ContainerSignalHandler(BaseCommandHandler):
    """Handler for sending a signal to a container."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        container_id = str(request.entities.get("container_id") or "")
        signal = str(request.entities.get("signal") or "")
        payload = self.gateway.containers_signal(app_name, region, container_id, signal)
        return self._with_mutation_preview(
            request,
            CommandResult("containers.signal", "success", f"Signal {signal} sent to {container_id}", payload, risk_level="high"),
        )
