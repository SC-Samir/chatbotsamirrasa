"""
Use-case command objects.

This module contains command data transfer objects used by the application
use cases to pass parameters between layers.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RestartAppCommand:
    app_name: str
    region: str
    scope: Optional[str] = None


@dataclass(frozen=True)
class ScaleAppCommand:
    app_name: str
    region: str
    container_name: str
    container_amount: str
    container_size: Optional[str] = None


@dataclass(frozen=True)
class DeleteAppCommand:
    app_name: str
    region: str


@dataclass(frozen=True)
class RenameAppCommand:
    app_name: str
    region: str
    new_name: str


@dataclass(frozen=True)
class ListEnvVarsCommand:
    app_name: str
    region: str
    aliases: bool = True


@dataclass(frozen=True)
class AddEnvVarCommand:
    app_name: str
    region: str
    variable_name: str
    variable_value: str
