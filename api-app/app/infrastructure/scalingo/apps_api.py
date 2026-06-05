"""Scalingo app-management API gateway.

This module provides both synchronous and asynchronous API gateways
for managing Scalingo applications. The async version is recommended
for use in async contexts like FastAPI endpoints.
"""
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

from app.application.dto import (
    AddEnvVarResultDTO,
    AppStatusDTO,
    ContainerDTO,
    DeleteResultDTO,
    EnvVarDTO,
    EnvVarsResultDTO,
    RenameResultDTO,
    RestartResultDTO,
    ScaleResultDTO,
)
from app.application.ports import AppManagementGateway
from app.domain import AppId, ContainerScale, ErrorCode, EnvVarInput, FailureReason, OperationError, OperationResult, Region
from app.infrastructure.scalingo.http_client import AsyncScalingoHTTPClient, ScalingoHTTPClient


class AppsAPI(AppManagementGateway):
    """
    Synchronous Scalingo app-management API gateway.
    
    This class uses the synchronous HTTP client and blocks the calling thread.
    For non-blocking operations, use AsyncAppsAPI instead.
    """
    
    def __init__(self, client: ScalingoHTTPClient):
        self.client = client

    def create_app(self, app_name: str, region: str) -> OperationResult[Dict[str, Any]]:
        region_vo = Region(region)
        payload = {"app": {"name": app_name}}
        return self.client.request("POST", region_vo, "/v1/apps", json_payload=payload)

    def trigger_deployment(
        self,
        app_name: str,
        region: str,
        github_repo: str,
        git_ref: str = "master",
    ) -> OperationResult[Dict[str, Any]]:
        region_vo = Region(region)
        if github_repo.endswith(".git"):
            github_repo = github_repo[:-4]
        github_repo = github_repo.rstrip("/")
        archive_url = f"{github_repo}/archive/{git_ref}.tar.gz"

        payload = {"source_url": archive_url, "git_ref": git_ref}
        return self.client.request(
            "POST",
            region_vo,
            f"/v1/apps/{app_name}/deployments",
            json_payload=payload,
        )

    def get_deployment_status(
        self, app_name: str, region: str, deployment_id: str
    ) -> OperationResult[Dict[str, Any]]:
        region_vo = Region(region)
        return self.client.request("GET", region_vo, f"/v1/apps/{app_name}/deployments/{deployment_id}")

    def get_logs_url(self, app_name: str, region: str) -> OperationResult[str]:
        region_vo = Region(region)
        result = self.client.request("GET", region_vo, f"/v1/apps/{app_name}/logs")
        if not result.success:
            return OperationResult.fail(result.error)

        logs_url = result.value.get("logs_url") if result.value else None
        if not logs_url:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.UPSTREAM,
                    message="Scalingo logs endpoint did not return logs_url",
                    code=ErrorCode.UPSTREAM_ERROR,
                    status_code=502,
                )
            )
        return OperationResult.ok(str(logs_url))

    def get_logs(
        self,
        app_name: str,
        region: str,
        n: int = 100,
        filter_param: Optional[str] = None,
        stream: bool = False,
    ) -> OperationResult[Dict[str, Any]]:
        logs_url_result = self.get_logs_url(app_name, region)
        if not logs_url_result.success:
            return OperationResult.fail(logs_url_result.error)

        params: Dict[str, Any] = {}
        if not stream and n != 100:
            params["n"] = n
        if filter_param:
            params["filter"] = filter_param

        from urllib.parse import urlencode

        logs_url = logs_url_result.value
        separator = "&" if "?" in logs_url else "?"
        query = urlencode(params)
        full_logs_url = f"{logs_url}{separator}{query}" if query else logs_url

        return OperationResult.ok(
            {
                "logs_url": full_logs_url,
                "parameters": params,
                "stream": stream,
                "app_name": app_name,
                "region": region,
            }
        )

    def restart_app(
        self, app_id: AppId, region: Region, scope: Optional[List[str]] = None
    ) -> OperationResult[RestartResultDTO]:
        payload = {"scope": scope} if scope else None
        result = self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/restart",
            json_payload=payload,
        )
        if not result.success:
            return OperationResult.fail(result.error)
        return OperationResult.ok(RestartResultDTO(accepted=True))

    def scale_app(
        self, app_id: AppId, region: Region, container: ContainerScale
    ) -> OperationResult[ScaleResultDTO]:
        payload = {
            "containers": [
                {
                    "name": container.name,
                    "amount": container.amount,
                    **({"size": container.size} if container.size else {}),
                }
            ]
        }
        result = self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/scale",
            json_payload=payload,
        )
        if not result.success:
            if (
                result.error
                and result.error.reason == FailureReason.VALIDATION
                and "is scaling" in str(result.error.details.get("response", "")).lower()
            ):
                return OperationResult.fail(
                    OperationError(
                        reason=FailureReason.CONFLICT,
                        message="Application is already scaling",
                        code=ErrorCode.ALREADY_EXISTS,
                        status_code=409,
                        details=result.error.details,
                    )
                )
            return OperationResult.fail(result.error)

        containers = result.value.get("containers", []) if result.value else []
        return OperationResult.ok(ScaleResultDTO(containers=containers))

    def delete_app(self, app_id: AppId, region: Region) -> OperationResult[DeleteResultDTO]:
        result = self.client.request(
            "DELETE",
            region,
            f"/v1/apps/{app_id.value}",
            params={"current_name": app_id.value},
        )
        if not result.success:
            return OperationResult.fail(result.error)
        return OperationResult.ok(DeleteResultDTO(deleted=True))

    def rename_app(self, app_id: AppId, region: Region, new_name: AppId) -> OperationResult[RenameResultDTO]:
        result = self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/rename",
            json_payload={"current_name": app_id.value, "new_name": new_name.value},
        )
        if not result.success:
            return OperationResult.fail(result.error)
        return OperationResult.ok(RenameResultDTO(app=result.value.get("app", {})))

    def get_app_status(self, app_id: AppId, region: Region) -> OperationResult[AppStatusDTO]:
        result = self.client.request("GET", region, f"/v1/apps/{app_id.value}")
        if not result.success:
            return OperationResult.fail(result.error)

        app_payload = (result.value or {}).get("app", {})
        return OperationResult.ok(
            AppStatusDTO(
                name=app_payload.get("name", app_id.value),
                status=app_payload.get("status", "unknown"),
                region=str(app_payload.get("region", region.value)),
            )
        )

    def get_containers_status(self, app_id: AppId, region: Region) -> OperationResult[List[ContainerDTO]]:
        result = self.client.request("GET", region, f"/v1/apps/{app_id.value}/ps")
        if not result.success:
            return OperationResult.fail(result.error)

        containers_payload = (result.value or {}).get("containers", [])
        containers: List[ContainerDTO] = []
        for index, payload in enumerate(containers_payload, start=1):
            size_info = payload.get("container_size") or {}
            containers.append(
                ContainerDTO(
                    type=payload.get("type", "unknown"),
                    state=payload.get("state", "unknown"),
                    label=payload.get("label", f"container-{index}"),
                    size=size_info.get("name"),
                    command=payload.get("command"),
                )
            )
        return OperationResult.ok(containers)

    def list_env_vars(
        self, app_id: AppId, region: Region, aliases: bool = True
    ) -> OperationResult[EnvVarsResultDTO]:
        result = self.client.request(
            "GET",
            region,
            f"/v1/apps/{app_id.value}/variables",
            params={"aliases": aliases},
        )
        if not result.success:
            return OperationResult.fail(result.error)

        variables_payload = (result.value or {}).get("variables", [])
        variables: List[EnvVarDTO] = []
        for payload in variables_payload:
            variables.append(
                EnvVarDTO(
                    name=payload.get("name", ""),
                    value=payload.get("value", ""),
                    var_id=payload.get("id"),
                )
            )
        return OperationResult.ok(EnvVarsResultDTO(variables=variables))

    def add_env_var(
        self, app_id: AppId, region: Region, env_var: EnvVarInput
    ) -> OperationResult[AddEnvVarResultDTO]:
        result = self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/variables",
            json_payload={"variable": {"name": env_var.name, "value": env_var.value}},
        )
        if not result.success:
            return OperationResult.fail(result.error)

        payload = (result.value or {}).get("variable", {})
        variable = EnvVarDTO(
            name=payload.get("name", env_var.name),
            value=payload.get("value", env_var.value),
            var_id=payload.get("id"),
        )
        return OperationResult.ok(AddEnvVarResultDTO(variable=variable))


class AsyncAppsAPI(AppManagementGateway):
    """
    Asynchronous Scalingo app-management API gateway.
    
    This class uses the async HTTP client and does not block the event loop.
    Recommended for use in async contexts like FastAPI endpoints.
    
    Usage:
        async with AsyncAppsAPI(client) as api:
            result = await api.create_app("my-app", "osc-fr1")
    """
    
    def __init__(self, client: AsyncScalingoHTTPClient):
        self.client = client
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()
    
    async def create_app(self, app_name: str, region: str) -> OperationResult[Dict[str, Any]]:
        region_vo = Region(region)
        payload = {"app": {"name": app_name}}
        return await self.client.request("POST", region_vo, "/v1/apps", json_payload=payload)

    async def trigger_deployment(
        self,
        app_name: str,
        region: str,
        github_repo: str,
        git_ref: str = "master",
    ) -> OperationResult[Dict[str, Any]]:
        region_vo = Region(region)
        if github_repo.endswith(".git"):
            github_repo = github_repo[:-4]
        github_repo = github_repo.rstrip("/")
        archive_url = f"{github_repo}/archive/{git_ref}.tar.gz"

        payload = {"source_url": archive_url, "git_ref": git_ref}
        return await self.client.request(
            "POST",
            region_vo,
            f"/v1/apps/{app_name}/deployments",
            json_payload=payload,
        )

    async def get_deployment_status(
        self, app_name: str, region: str, deployment_id: str
    ) -> OperationResult[Dict[str, Any]]:
        region_vo = Region(region)
        return await self.client.request("GET", region_vo, f"/v1/apps/{app_name}/deployments/{deployment_id}")

    async def get_logs_url(self, app_name: str, region: str) -> OperationResult[str]:
        region_vo = Region(region)
        result = await self.client.request("GET", region_vo, f"/v1/apps/{app_name}/logs")
        if not result.success:
            return OperationResult.fail(result.error)

        logs_url = result.value.get("logs_url") if result.value else None
        if not logs_url:
            return OperationResult.fail(
                OperationError(
                    reason=FailureReason.UPSTREAM,
                    message="Scalingo logs endpoint did not return logs_url",
                    code=ErrorCode.UPSTREAM_ERROR,
                    status_code=502,
                )
            )
        return OperationResult.ok(str(logs_url))

    async def get_logs(
        self,
        app_name: str,
        region: str,
        n: int = 100,
        filter_param: Optional[str] = None,
        stream: bool = False,
    ) -> OperationResult[Dict[str, Any]]:
        logs_url_result = await self.get_logs_url(app_name, region)
        if not logs_url_result.success:
            return OperationResult.fail(logs_url_result.error)

        params: Dict[str, Any] = {}
        if not stream and n != 100:
            params["n"] = n
        if filter_param:
            params["filter"] = filter_param

        logs_url = logs_url_result.value
        separator = "&" if "?" in logs_url else "?"
        query = urlencode(params)
        full_logs_url = f"{logs_url}{separator}{query}" if query else logs_url

        return OperationResult.ok(
            {
                "logs_url": full_logs_url,
                "parameters": params,
                "stream": stream,
                "app_name": app_name,
                "region": region,
            }
        )

    async def restart_app(
        self, app_id: AppId, region: Region, scope: Optional[List[str]] = None
    ) -> OperationResult[RestartResultDTO]:
        payload = {"scope": scope} if scope else None
        result = await self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/restart",
            json_payload=payload,
        )
        if not result.success:
            return OperationResult.fail(result.error)
        return OperationResult.ok(RestartResultDTO(accepted=True))

    async def scale_app(
        self, app_id: AppId, region: Region, container: ContainerScale
    ) -> OperationResult[ScaleResultDTO]:
        payload = {
            "containers": [
                {
                    "name": container.name,
                    "amount": container.amount,
                    **({"size": container.size} if container.size else {}),
                }
            ]
        }
        result = await self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/scale",
            json_payload=payload,
        )
        if not result.success:
            if (
                result.error
                and result.error.reason == FailureReason.VALIDATION
                and "is scaling" in str(result.error.details.get("response", "")).lower()
            ):
                return OperationResult.fail(
                    OperationError(
                        reason=FailureReason.CONFLICT,
                        message="Application is already scaling",
                        code=ErrorCode.ALREADY_EXISTS,
                        status_code=409,
                        details=result.error.details,
                    )
                )
            return OperationResult.fail(result.error)

        containers = result.value.get("containers", []) if result.value else []
        return OperationResult.ok(ScaleResultDTO(containers=containers))

    async def delete_app(self, app_id: AppId, region: Region) -> OperationResult[DeleteResultDTO]:
        result = await self.client.request(
            "DELETE",
            region,
            f"/v1/apps/{app_id.value}",
            params={"current_name": app_id.value},
        )
        if not result.success:
            return OperationResult.fail(result.error)
        return OperationResult.ok(DeleteResultDTO(deleted=True))

    async def rename_app(self, app_id: AppId, region: Region, new_name: AppId) -> OperationResult[RenameResultDTO]:
        result = await self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/rename",
            json_payload={"current_name": app_id.value, "new_name": new_name.value},
        )
        if not result.success:
            return OperationResult.fail(result.error)
        return OperationResult.ok(RenameResultDTO(app=result.value.get("app", {})))

    async def get_app_status(self, app_id: AppId, region: Region) -> OperationResult[AppStatusDTO]:
        result = await self.client.request("GET", region, f"/v1/apps/{app_id.value}")
        if not result.success:
            return OperationResult.fail(result.error)

        app_payload = (result.value or {}).get("app", {})
        return OperationResult.ok(
            AppStatusDTO(
                name=app_payload.get("name", app_id.value),
                status=app_payload.get("status", "unknown"),
                region=str(app_payload.get("region", region.value)),
            )
        )

    async def get_containers_status(self, app_id: AppId, region: Region) -> OperationResult[List[ContainerDTO]]:
        result = await self.client.request("GET", region, f"/v1/apps/{app_id.value}/ps")
        if not result.success:
            return OperationResult.fail(result.error)

        containers_payload = (result.value or {}).get("containers", [])
        containers: List[ContainerDTO] = []
        for index, payload in enumerate(containers_payload, start=1):
            size_info = payload.get("container_size") or {}
            containers.append(
                ContainerDTO(
                    type=payload.get("type", "unknown"),
                    state=payload.get("state", "unknown"),
                    label=payload.get("label", f"container-{index}"),
                    size=size_info.get("name"),
                    command=payload.get("command"),
                )
            )
        return OperationResult.ok(containers)

    async def list_env_vars(
        self, app_id: AppId, region: Region, aliases: bool = True
    ) -> OperationResult[EnvVarsResultDTO]:
        result = await self.client.request(
            "GET",
            region,
            f"/v1/apps/{app_id.value}/variables",
            params={"aliases": aliases},
        )
        if not result.success:
            return OperationResult.fail(result.error)

        variables_payload = (result.value or {}).get("variables", [])
        variables: List[EnvVarDTO] = []
        for payload in variables_payload:
            variables.append(
                EnvVarDTO(
                    name=payload.get("name", ""),
                    value=payload.get("value", ""),
                    var_id=payload.get("id"),
                )
            )
        return OperationResult.ok(EnvVarsResultDTO(variables=variables))

    async def add_env_var(
        self, app_id: AppId, region: Region, env_var: EnvVarInput
    ) -> OperationResult[AddEnvVarResultDTO]:
        result = await self.client.request(
            "POST",
            region,
            f"/v1/apps/{app_id.value}/variables",
            json_payload={"variable": {"name": env_var.name, "value": env_var.value}},
        )
        if not result.success:
            return OperationResult.fail(result.error)

        payload = (result.value or {}).get("variable", {})
        variable = EnvVarDTO(
            name=payload.get("name", env_var.name),
            value=payload.get("value", env_var.value),
            var_id=payload.get("id"),
        )
        return OperationResult.ok(AddEnvVarResultDTO(variable=variable))
