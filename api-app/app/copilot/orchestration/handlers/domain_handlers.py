"""
Domain command handlers.

This module contains all command handlers related to domain management.
"""
from __future__ import annotations

from typing import Any, Dict

from app.copilot.contracts import CommandRequest, CommandResult
from app.copilot.orchestration.handlers.base import BaseCommandHandler, HandlerConfig, handler


@handler(
    "domains.list",
    HandlerConfig(
        requires_app_region=True,
        is_mutating=False,
    ),
)
class DomainListHandler(BaseCommandHandler):
    """Handler for listing domains."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        payload = self.gateway.domains_list(app_name, region)
        return CommandResult("domains.list", "success", "Domains loaded", payload)


@handler(
    "domains.create",
    HandlerConfig(
        required_entities=("domain",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
    ),
)
class DomainCreateHandler(BaseCommandHandler):
    """Handler for creating a domain."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        domain_name = str(request.entities.get("domain") or "")
        domain_payload: Dict[str, Any] = {"name": domain_name}
        if "canonical" in request.entities:
            domain_payload["canonical"] = bool(request.entities.get("canonical"))
        if "letsencrypt_enabled" in request.entities:
            domain_payload["letsencrypt_enabled"] = bool(request.entities.get("letsencrypt_enabled"))
        payload = self.gateway.domains_create(app_name, region, {"domain": domain_payload})
        return self._with_mutation_preview(
            request,
            CommandResult("domains.create", "success", f"Domain {domain_name} creation requested", payload),
        )


@handler(
    "domains.delete",
    HandlerConfig(
        required_entities=("domain",),
        requires_app_region=True,
        idempotent=False,
        is_mutating=True,
        is_destructive=True,
    ),
)
class DomainDeleteHandler(BaseCommandHandler):
    """Handler for deleting a domain."""

    def handle(self, request: CommandRequest) -> CommandResult:
        app_name, region = self._resolve_app_region(request)
        domain = str(request.entities.get("domain") or "")
        payload = self.gateway.domains_delete(app_name, region, domain)
        return self._with_mutation_preview(
            request,
            CommandResult("domains.delete", "success", f"Domain {domain} delete requested", payload, risk_level="high"),
        )
