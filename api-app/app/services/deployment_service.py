"""Deployment service backed by the typed Scalingo gateway."""
from typing import Any, Dict, Optional

from app.infrastructure.scalingo import AppsAPI


class DeploymentService:
    """Service for deployment orchestration."""

    def __init__(self, apps_api: AppsAPI):
        self.apps_api = apps_api

    def create_app(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        result = self.apps_api.create_app(app_name, region)
        return result.value if result.success else None

    def trigger_deployment(
        self, app_name: str, region: str, github_repo: str, git_ref: str = "master"
    ) -> Optional[Dict[str, Any]]:
        result = self.apps_api.trigger_deployment(app_name, region, github_repo, git_ref)
        return result.value if result.success else None

    def get_deployment_status(self, app_name: str, region: str, deployment_id: str) -> Optional[Dict[str, Any]]:
        result = self.apps_api.get_deployment_status(app_name, region, deployment_id)
        return result.value if result.success else None

    def validate_deployment_params(self, app_name: str, region: str, github_repo: str) -> Optional[str]:
        if not all([app_name, region, github_repo]):
            return "To deploy, I need the app name, region and GitHub repo."
        return None

    def build_archive_url(self, github_repo: str, git_ref: str) -> str:
        if github_repo.endswith(".git"):
            github_repo = github_repo[:-4]
        if github_repo.endswith("/"):
            github_repo = github_repo[:-1]
        return f"{github_repo}/archive/{git_ref}.tar.gz"
