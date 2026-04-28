"""Application DTOs for app-management use-cases."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AppStatusDTO:
    name: str
    status: str
    region: str


@dataclass(frozen=True)
class ContainerDTO:
    type: str
    state: str
    label: str
    size: Optional[str] = None
    command: Optional[str] = None


@dataclass(frozen=True)
class RestartResultDTO:
    accepted: bool


@dataclass(frozen=True)
class ScaleResultDTO:
    containers: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DeleteResultDTO:
    deleted: bool


@dataclass(frozen=True)
class RenameResultDTO:
    app: Dict[str, Any]


@dataclass(frozen=True)
class EnvVarDTO:
    name: str
    value: str
    var_id: Optional[str] = None


@dataclass(frozen=True)
class EnvVarsResultDTO:
    variables: List[EnvVarDTO]


@dataclass(frozen=True)
class AddEnvVarResultDTO:
    variable: EnvVarDTO
