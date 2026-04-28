from app.application.commands import AddEnvVarCommand, RenameAppCommand
from app.application.use_cases.app_management import AddEnvVar, RenameApp
from app.domain import FailureReason, OperationResult


class NoopGateway:
    def rename_app(self, app_id, region, new_name):  # pragma: no cover - should not be called here
        return OperationResult.ok(None)

    def add_env_var(self, app_id, region, env_var):  # pragma: no cover - should not be called here
        return OperationResult.ok(None)


def test_rename_usecase_rejects_invalid_new_name():
    use_case = RenameApp(NoopGateway())

    result = use_case.execute(
        RenameAppCommand(app_name="demo-app", region="osc-fr1", new_name="INVALID_NAME")
    )

    assert result.success is False
    assert result.error.reason == FailureReason.VALIDATION


def test_add_env_var_usecase_rejects_invalid_variable_name():
    use_case = AddEnvVar(NoopGateway())

    result = use_case.execute(
        AddEnvVarCommand(
            app_name="demo-app",
            region="osc-fr1",
            variable_name="INVALID-NAME",
            variable_value="value",
        )
    )

    assert result.success is False
    assert result.error.reason == FailureReason.VALIDATION
