"""
Modèles de données pour l'application.
"""
from typing import Optional, Dict, Any, List
try:
    from pydantic.v1 import BaseModel, validator, Field
except ImportError:  # pragma: no cover
    from pydantic import BaseModel, validator, Field
from enum import Enum
import re


class Region(str, Enum):
    """Régions Scalingo supportées."""
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


class AppContext(BaseModel):
    """Contexte de l'application mémorisé."""
    app_name: Optional[str] = None
    region: Optional[Region] = None
    github_repo: Optional[str] = None
    git_ref: str = "master"


class DeploymentRequest(BaseModel):
    """Requête de déploiement."""
    app_name: str
    region: Region
    github_repo: str
    git_ref: str = "master"
    
    @validator('app_name')
    def validate_app_name(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Le nom de l'app doit contenir uniquement des lettres minuscules, chiffres et tirets")
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Le nom de l'app doit faire entre 3 et 30 caractères")
        return v
    
    @validator('github_repo')
    def validate_github_repo(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("L'URL GitHub doit commencer par http:// ou https://")
        if 'github.com' not in v:
            raise ValueError("L'URL doit être un repository GitHub")
        return v


class LogsRequest(BaseModel):
    """Requête de récupération des logs."""
    app_name: str = Field(..., min_length=3, max_length=30, regex=r'^[a-z0-9-]+$')
    region: Region
    n: int = Field(default=100, ge=1, le=10000)
    filter_param: Optional[str] = Field(None, max_length=100)
    stream: bool = False
    
    @validator('filter_param')
    def validate_filter_param(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError("Le filtre ne peut contenir que des lettres, chiffres, tirets et underscores")
        return v


class LogsResponse(BaseModel):
    """Réponse des logs."""
    logs_url: str
    parameters: Dict[str, Any]
    stream: bool
    app_name: str
    region: Region


class DeploymentInfo(BaseModel):
    """Informations de déploiement."""
    id: str
    status: DeploymentStatus
    app_name: str
    region: Region


class WebSocketMessage(BaseModel):
    """Message WebSocket."""
    message: str
    data: Optional[Dict[str, Any]] = None


class IntentResponse(BaseModel):
    """Réponse d'intent NLU v2."""
    intent_top1: Dict[str, Any]
    intent_ranking: List[Dict[str, Any]]
    decision: Dict[str, Any]
    entities: List[Dict[str, Any]]
    text_normalized: str
    model_info: Dict[str, Any]

    @property
    def accepted_intent(self) -> str:
        return str(self.decision.get("accepted_intent", "nlu_fallback"))
