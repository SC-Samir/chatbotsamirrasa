"""
Protocoles pour définir les contrats d'interface.
"""
from typing import Protocol, Optional, Dict, Any
from app.models import LogsRequest, LogsResponse, DeploymentRequest


class ScalingoManagerProtocol(Protocol):
    """Protocole pour le gestionnaire Scalingo."""
    
    def create_app(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        """Crée une nouvelle application."""
        ...
    
    def trigger_deployment(self, app_name: str, region: str, github_repo: str, git_ref: str = "master") -> Optional[Dict[str, Any]]:
        """Déclenche un déploiement."""
        ...
    
    def get_deployment_status(self, app_name: str, region: str, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'un déploiement."""
        ...
    
    def get_logs(self, app_name: str, region: str, n: int = 100, filter_param: Optional[str] = None, stream: bool = False) -> Optional[Dict[str, Any]]:
        """Récupère les informations des logs."""
        ...


class LogsServiceProtocol(Protocol):
    """Protocole pour le service de logs."""
    
    async def get_logs_info(self, request: LogsRequest) -> Optional[LogsResponse]:
        """Récupère les informations des logs."""
        ...
    
    async def fetch_and_display_logs(self, websocket, logs_url: str, stream_mode: bool = False) -> None:
        """Récupère et affiche les logs."""
        ...


class IntentHandlerProtocol(Protocol):
    """Protocole pour les handlers d'intent."""
    
    async def handle(self, websocket, intent_response, context) -> bool:
        """Traite un intent."""
        ...


class WebSocketHandlerProtocol(Protocol):
    """Protocole pour le gestionnaire WebSocket."""
    
    async def handle_connection(self, websocket) -> None:
        """Gère une connexion WebSocket."""
        ...


class DeploymentServiceProtocol(Protocol):
    """Protocole pour le service de déploiement."""
    
    async def deploy_application(self, request: DeploymentRequest) -> Optional[str]:
        """Déploie une application."""
        ...
    
    async def create_and_deploy(self, request: DeploymentRequest) -> Optional[str]:
        """Crée et déploie une application."""
        ...
