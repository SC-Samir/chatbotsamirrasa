from app.domain import AppId, ContainerScale, EnvVarInput, FailureReason
from app.domain.value_objects import Region
from app.infrastructure.scalingo.apps_api import AppsAPI
from app.infrastructure.scalingo.http_client import ScalingoHTTPClient


class DummyTokenProvider:
    def get_token(self) -> str:
        return "token"

    def refresh(self) -> str:
        return "token"


def build_api() -> AppsAPI:
    client = ScalingoHTTPClient(DummyTokenProvider())
    return AppsAPI(client)


def test_apps_api_restart_scale_delete_rename_and_env_vars(httpx_mock):
    api = build_api()

    base = "https://api.osc-fr1.scalingo.com"
    httpx_mock.add_response(method="POST", url=f"{base}/v1/apps/demo/restart", status_code=202)
    httpx_mock.add_response(
        method="POST",
        url=f"{base}/v1/apps/demo/scale",
        status_code=200,
        json={"containers": [{"name": "web", "amount": 2}]},
    )
    httpx_mock.add_response(
        method="DELETE",
        url=f"{base}/v1/apps/demo?current_name=demo",
        status_code=204,
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base}/v1/apps/demo/rename",
        status_code=200,
        json={"app": {"name": "demo-new", "status": "running", "region": "osc-fr1"}},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{base}/v1/apps/demo/variables?aliases=true",
        status_code=200,
        json={"variables": [{"name": "RAILS_ENV", "value": "production", "id": "var-1"}]},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base}/v1/apps/demo/variables",
        status_code=201,
        json={"variable": {"name": "FOO", "value": "BAR", "id": "var-2"}},
    )

    restart = api.restart_app(AppId("demo"), Region.OSC_FR1)
    scale = api.scale_app(AppId("demo"), Region.OSC_FR1, ContainerScale(name="web", amount=2))
    delete = api.delete_app(AppId("demo"), Region.OSC_FR1)
    rename = api.rename_app(AppId("demo"), Region.OSC_FR1, AppId("demo-new"))
    envs = api.list_env_vars(AppId("demo"), Region.OSC_FR1)
    add_env = api.add_env_var(AppId("demo"), Region.OSC_FR1, EnvVarInput(name="FOO", value="BAR"))

    assert restart.success is True
    assert scale.success is True and scale.value.containers[0]["amount"] == 2
    assert delete.success is True and delete.value.deleted is True
    assert rename.success is True and rename.value.app["name"] == "demo-new"
    assert envs.success is True and envs.value.variables[0].name == "RAILS_ENV"
    assert add_env.success is True and add_env.value.variable.var_id == "var-2"


def test_scale_conflict_is_mapped_from_422_payload(httpx_mock):
    api = build_api()
    base = "https://api.osc-fr1.scalingo.com"

    httpx_mock.add_response(
        method="POST",
        url=f"{base}/v1/apps/demo/scale",
        status_code=422,
        json={"errors": {"app": ["application is scaling"]}},
    )

    result = api.scale_app(AppId("demo"), Region.OSC_FR1, ContainerScale(name="web", amount=2))

    assert result.success is False
    assert result.error.reason == FailureReason.CONFLICT
