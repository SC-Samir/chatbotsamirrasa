"""
Service de gestion des déploiements.
"""
from typing import Optional, Dict, Any
from app.scalingo_manager import ScalingoManager
from app.models import AppContext


class DeploymentService:
    """Service pour la gestion des déploiements."""
    
    def __init__(self, scalingo_manager: ScalingoManager):
        self.scalingo_manager = scalingo_manager
    
    def create_app(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        """Crée une nouvelle application."""
        return self.scalingo_manager.create_app(app_name, region)
    
    def trigger_deployment(self, app_name: str, region: str, github_repo: str, 
                          git_ref: str = "master") -> Optional[Dict[str, Any]]:
        """Déclenche un déploiement."""
        return self.scalingo_manager.trigger_deployment(app_name, region, github_repo, git_ref)
    
    def get_deployment_status(self, app_name: str, region: str, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'un déploiement."""
        return self.scalingo_manager.get_deployment_status(app_name, region, deployment_id)
    
    def validate_deployment_params(self, app_name: str, region: str, github_repo: str) -> Optional[str]:
        """Valide les paramètres de déploiement."""
        if not all([app_name, region, github_repo]):
            return "To deploy, I need the app name, region and GitHub repo."
        return None
    
    def build_archive_url(self, github_repo: str, git_ref: str) -> str:
        """Construit l'URL d'archive GitHub."""
        if github_repo.endswith('.git'):
            github_repo = github_repo[:-4]
        if github_repo.endswith('/'):
            github_repo = github_repo[:-1]
        return f"{github_repo}/archive/{git_ref}.tar.gz"
