"""Application gateway ports."""
from typing import List, Optional, Protocol

from app.application.dto import (
    AddEnvVarResultDTO,
    AppStatusDTO,
    ContainerDTO,
    DeleteResultDTO,
    EnvVarsResultDTO,
    RenameResultDTO,
    RestartResultDTO,
    ScaleResultDTO,
)
from app.domain import AppId, ContainerScale, EnvVarInput, OperationResult, Region


class AppManagementGateway(Protocol):
    def restart_app(
        self, app_id: AppId, region: Region, scope: Optional[List[str]] = None
    ) -> OperationResult[RestartResultDTO]:
        ...

    def scale_app(
        self, app_id: AppId, region: Region, container: ContainerScale
    ) -> OperationResult[ScaleResultDTO]:
        ...

    def delete_app(self, app_id: AppId, region: Region) -> OperationResult[DeleteResultDTO]:
        ...

    def rename_app(
        self, app_id: AppId, region: Region, new_name: AppId
    ) -> OperationResult[RenameResultDTO]:
        ...

    def get_app_status(self, app_id: AppId, region: Region) -> OperationResult[AppStatusDTO]:
        ...

    def get_containers_status(
        self, app_id: AppId, region: Region
    ) -> OperationResult[List[ContainerDTO]]:
        ...

    def list_env_vars(
        self, app_id: AppId, region: Region, aliases: bool = True
    ) -> OperationResult[EnvVarsResultDTO]:
        ...

    def add_env_var(
        self, app_id: AppId, region: Region, env_var: EnvVarInput
    ) -> OperationResult[AddEnvVarResultDTO]:
        ...
