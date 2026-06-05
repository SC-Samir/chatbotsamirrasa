"""Domain value objects used by application use-cases."""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional

from app.domain.errors import DomainValidationError

_APP_NAME_RE = re.compile(r"^[a-z0-9-]+$")
_ENV_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Region(str, Enum):
    OSC_FR1 = "osc-fr1"
    OSC_SECNUM_FR1 = "osc-secnum-fr1"


class DeploymentStatus(str, Enum):
    """Statuts de déploiement Scalingo."""
    QUEUED = "queued"
    BUILDING = "building"
    PUSHING = "pushing"
    STARTING = "starting"
    SUCCESS = "success"
    CRASHED_ERROR = "crashed-error"
    TIMEOUT_ERROR = "timeout-error"
    BUILD_ERROR = "build-error"
    ABORTED = "aborted"
    
    @classmethod
    def is_final_status(cls, status: str) -> bool:
        """Vérifie si le déploiement a atteint un état final."""
        return status in [
            cls.SUCCESS,
            cls.CRASHED_ERROR,
            cls.TIMEOUT_ERROR,
            cls.BUILD_ERROR,
            cls.ABORTED
        ]
    
    @classmethod
    def is_error_status(cls, status: str) -> bool:
        """Vérifie si le statut indique une erreur."""
        return status in [
            cls.CRASHED_ERROR,
            cls.TIMEOUT_ERROR,
            cls.BUILD_ERROR
        ]


@dataclass(frozen=True)
class AppId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise DomainValidationError("App name cannot be empty.")
        candidate = self.value.strip()
        if len(candidate) < 3 or len(candidate) > 63:
            raise DomainValidationError("App name must contain 3 to 63 characters.")
        if not _APP_NAME_RE.match(candidate):
            raise DomainValidationError(
                "App name can only contain lowercase letters, numbers and hyphens."
            )


@dataclass(frozen=True)
class ContainerScale:
    name: str
    amount: int
    size: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise DomainValidationError("Container name is required.")
        if self.amount < 0:
            raise DomainValidationError("Container amount must be >= 0.")


@dataclass(frozen=True)
class EnvVarInput:
    name: str
    value: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise DomainValidationError("Environment variable name cannot be empty.")
        if not _ENV_VAR_RE.match(self.name):
            raise DomainValidationError(
                "Environment variable name must match [A-Za-z_][A-Za-z0-9_]*."
            )
        if len(self.name) > 64:
            raise DomainValidationError("Environment variable name cannot exceed 64 characters.")
        if self.value is None:
            raise DomainValidationError("Environment variable value cannot be null.")
        if len(self.value) > 8192:
            raise DomainValidationError("Environment variable value cannot exceed 8192 characters.")
