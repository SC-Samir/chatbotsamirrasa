"""Validation helpers for application commands."""
from typing import List, Optional

from app.domain import AppId, ContainerScale, DomainValidationError, EnvVarInput, Region


def parse_app_id(value: str) -> AppId:
    return AppId(value=value)


def parse_region(value: str) -> Region:
    try:
        return Region(value)
    except ValueError as exc:
        supported = ", ".join(region.value for region in Region)
        raise DomainValidationError(f"Unknown region '{value}'. Supported regions: {supported}") from exc


def parse_scope(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None
    scope = [item.strip() for item in value.split(",") if item.strip()]
    return scope or None


def parse_container_scale(name: str, amount: str, size: Optional[str] = None) -> ContainerScale:
    try:
        parsed_amount = int(amount)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(f"Invalid container amount '{amount}'. Expected an integer.") from exc

    normalized_size = size.upper() if size else None
    return ContainerScale(name=name, amount=parsed_amount, size=normalized_size)


def parse_env_var(name: str, value: str) -> EnvVarInput:
    return EnvVarInput(name=name, value=value)
