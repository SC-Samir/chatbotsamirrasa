import httpx

from app.domain.value_objects import Region
from app.infrastructure.scalingo.http_client import ScalingoHTTPClient


class DummyTokenProvider:
    def __init__(self):
        self.refresh_calls = 0

    def get_token(self) -> str:
        return "token"

    def refresh(self) -> str:
        self.refresh_calls += 1
        return "refreshed-token"


def test_request_retries_once_on_401(httpx_mock):
    provider = DummyTokenProvider()
    client = ScalingoHTTPClient(provider)

    url = "https://api.osc-fr1.scalingo.com/v1/apps/demo"
    httpx_mock.add_response(method="GET", url=url, status_code=401, json={"error": "expired"})
    httpx_mock.add_response(method="GET", url=url, status_code=200, json={"app": {"name": "demo"}})

    result = client.request("GET", Region.OSC_FR1, "/v1/apps/demo")

    assert result.success is True
    assert result.value == {"app": {"name": "demo"}}
    assert provider.refresh_calls == 1


def test_request_fails_after_single_401_retry(httpx_mock):
    provider = DummyTokenProvider()
    client = ScalingoHTTPClient(provider)

    url = "https://api.osc-fr1.scalingo.com/v1/apps/demo"
    httpx_mock.add_response(method="GET", url=url, status_code=401, json={"error": "expired-1"})
    httpx_mock.add_response(method="GET", url=url, status_code=401, json={"error": "expired-2"})

    result = client.request("GET", Region.OSC_FR1, "/v1/apps/demo")

    assert result.success is False
    assert result.error.status_code == 401
    assert provider.refresh_calls == 1


class FailingTokenProvider:
    def get_token(self) -> str:
        raise RuntimeError("token exchange timeout")

    def refresh(self) -> str:
        return "unused"


def test_request_returns_operation_error_when_token_provider_fails():
    client = ScalingoHTTPClient(FailingTokenProvider())

    result = client.request("GET", Region.OSC_FR1, "/v1/apps/demo")

    assert result.success is False
    assert result.error.status_code == 503
    assert result.error.reason.value == "transient"
    assert "Unable to get Scalingo bearer token" in result.error.message
