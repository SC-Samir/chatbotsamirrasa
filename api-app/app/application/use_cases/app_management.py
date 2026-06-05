"""App-management use-cases."""
from app.application.commands import (
    AddEnvVarCommand,
    DeleteAppCommand,
    ListEnvVarsCommand,
    RenameAppCommand,
    RestartAppCommand,
    ScaleAppCommand,
)
from app.application.dto import (
    AddEnvVarResultDTO,
    DeleteResultDTO,
    EnvVarsResultDTO,
    RenameResultDTO,
    RestartResultDTO,
    ScaleResultDTO,
)
from app.application.ports import AppManagementGateway
from app.application.validators import (
    parse_app_id,
    parse_container_scale,
    parse_env_var,
    parse_region,
    parse_scope,
)
from app.domain import ErrorCode, DomainValidationError, FailureReason, OperationError, OperationResult


def _validation_error(message: str) -> OperationError:
    return OperationError(
        reason=FailureReason.VALIDATION,
        message=message,
        code=ErrorCode.VALIDATION_ERROR,
        status_code=400,
    )


class RestartApp:
    def __init__(self, gateway: AppManagementGateway):
        self.gateway = gateway

    def execute(self, command: RestartAppCommand) -> OperationResult[RestartResultDTO]:
        try:
            app_id = parse_app_id(command.app_name)
            region = parse_region(command.region)
            scope = parse_scope(command.scope)
        except DomainValidationError as exc:
            return OperationResult.fail(_validation_error(str(exc)))

        return self.gateway.restart_app(app_id, region, scope)


class ScaleApp:
    def __init__(self, gateway: AppManagementGateway):
        self.gateway = gateway

    def execute(self, command: ScaleAppCommand) -> OperationResult[ScaleResultDTO]:
        try:
            app_id = parse_app_id(command.app_name)
            region = parse_region(command.region)
            container = parse_container_scale(
                command.container_name,
                command.container_amount,
                command.container_size,
            )
        except DomainValidationError as exc:
            return OperationResult.fail(_validation_error(str(exc)))

        return self.gateway.scale_app(app_id, region, container)


class DeleteApp:
    def __init__(self, gateway: AppManagementGateway):
        self.gateway = gateway

    def execute(self, command: DeleteAppCommand) -> OperationResult[DeleteResultDTO]:
        try:
            app_id = parse_app_id(command.app_name)
            region = parse_region(command.region)
        except DomainValidationError as exc:
            return OperationResult.fail(_validation_error(str(exc)))

        return self.gateway.delete_app(app_id, region)


class RenameApp:
    def __init__(self, gateway: AppManagementGateway):
        self.gateway = gateway

    def execute(self, command: RenameAppCommand) -> OperationResult[RenameResultDTO]:
        try:
            app_id = parse_app_id(command.app_name)
            region = parse_region(command.region)
            new_name = parse_app_id(command.new_name)
        except DomainValidationError as exc:
            return OperationResult.fail(_validation_error(str(exc)))

        return self.gateway.rename_app(app_id, region, new_name)


class ListEnvVars:
    def __init__(self, gateway: AppManagementGateway):
        self.gateway = gateway

    def execute(self, command: ListEnvVarsCommand) -> OperationResult[EnvVarsResultDTO]:
        try:
            app_id = parse_app_id(command.app_name)
            region = parse_region(command.region)
        except DomainValidationError as exc:
            return OperationResult.fail(_validation_error(str(exc)))

        return self.gateway.list_env_vars(app_id, region, aliases=command.aliases)


class AddEnvVar:
    def __init__(self, gateway: AppManagementGateway):
        self.gateway = gateway

    def execute(self, command: AddEnvVarCommand) -> OperationResult[AddEnvVarResultDTO]:
        try:
            app_id = parse_app_id(command.app_name)
            region = parse_region(command.region)
            env_var = parse_env_var(command.variable_name, command.variable_value)
        except DomainValidationError as exc:
            return OperationResult.fail(_validation_error(str(exc)))

        return self.gateway.add_env_var(app_id, region, env_var)
