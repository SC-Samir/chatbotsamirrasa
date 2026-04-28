"""Compatibility facade over the new Scalingo infrastructure layer."""
from typing import Any, Dict, List, Optional

from app.domain import AppId, ContainerScale, EnvVarInput, Region
from app.infrastructure.scalingo import AppsAPI, ScalingoHTTPClient, build_default_token_provider


class ScalingoManager:
    """
    Backward-compatible facade used by legacy services.

    The previous monolithic implementation has been replaced by:
    - AuthTokenProvider
    - ScalingoHTTPClient
    - AppsAPI gateway
    """

    def __init__(self):
        token_provider = build_default_token_provider()
        http_client = ScalingoHTTPClient(token_provider)
        self.apps_api = AppsAPI(http_client)

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

    def get_logs_url(self, app_name: str, region: str) -> Optional[str]:
        result = self.apps_api.get_logs_url(app_name, region)
        return result.value if result.success else None

    def get_logs(
        self,
        app_name: str,
        region: str,
        n: int = 100,
        filter_param: str = None,
        stream: bool = False,
    ) -> Optional[Dict[str, Any]]:
        result = self.apps_api.get_logs(app_name, region, n=n, filter_param=filter_param, stream=stream)
        return result.value if result.success else None

    def restart_app(self, app_name: str, region: str, scope: List[str] = None) -> Optional[Dict[str, Any]]:
        try:
            result = self.apps_api.restart_app(AppId(app_name), Region(region), scope)
        except ValueError:
            return None
        return {"status": "accepted"} if result.success else None

    def scale_app(self, app_name: str, region: str, containers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not containers:
            return {"error": "validation_error", "message": "No containers provided"}

        container = containers[0]
        try:
            scale = ContainerScale(
                name=container["name"],
                amount=int(container["amount"]),
                size=container.get("size"),
            )
            result = self.apps_api.scale_app(AppId(app_name), Region(region), scale)
        except Exception as exc:
            return {"error": "validation_error", "message": str(exc)}

        if result.success:
            return {"containers": result.value.containers}
        if result.error is None:
            return None
        return {
            "error": result.error.reason.value,
            "message": result.error.message,
            "details": result.error.details,
        }

    def delete_app(self, app_name: str, region: str) -> bool:
        try:
            result = self.apps_api.delete_app(AppId(app_name), Region(region))
        except Exception:
            return False
        return result.success and bool(result.value.deleted)

    def rename_app(self, app_name: str, region: str, new_name: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.apps_api.rename_app(AppId(app_name), Region(region), AppId(new_name))
        except Exception as exc:
            return {"error": "validation_error", "message": str(exc)}

        if result.success:
            return {"app": result.value.app}
        if result.error is None:
            return None
        return {
            "error": result.error.reason.value,
            "message": result.error.message,
            "details": result.error.details,
        }

    def get_app_status(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.apps_api.get_app_status(AppId(app_name), Region(region))
        except Exception:
            return None
        if not result.success:
            return None
        return {
            "app": {
                "name": result.value.name,
                "status": result.value.status,
                "region": result.value.region,
            }
        }

    def get_containers_status(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.apps_api.get_containers_status(AppId(app_name), Region(region))
        except Exception:
            return None
        if not result.success:
            return None
        return {
            "containers": [
                {
                    "type": item.type,
                    "state": item.state,
                    "label": item.label,
                    "container_size": {"name": item.size} if item.size else {},
                    "command": item.command,
                }
                for item in result.value
            ]
        }

    def get_app_variables(self, app_name: str, region: str, aliases: bool = True) -> Optional[Dict[str, Any]]:
        try:
            result = self.apps_api.list_env_vars(AppId(app_name), Region(region), aliases)
        except Exception as exc:
            return {"error": "validation_error", "message": str(exc)}

        if not result.success:
            return {
                "error": result.error.reason.value,
                "message": result.error.message,
                "details": result.error.details,
            }
        return {
            "variables": [
                {"name": item.name, "value": item.value, "id": item.var_id}
                for item in result.value.variables
            ]
        }

    def add_app_variable(
        self, app_name: str, region: str, variable_name: str, variable_value: str
    ) -> Optional[Dict[str, Any]]:
        try:
            result = self.apps_api.add_env_var(
                AppId(app_name),
                Region(region),
                EnvVarInput(name=variable_name, value=variable_value),
            )
        except Exception as exc:
            return {"error": "validation_error", "message": str(exc)}

        if not result.success:
            return {
                "error": result.error.reason.value,
                "message": result.error.message,
                "details": result.error.details,
            }
        return {
            "variable": {
                "name": result.value.variable.name,
                "value": result.value.variable.value,
                "id": result.value.variable.var_id,
            }
        }
