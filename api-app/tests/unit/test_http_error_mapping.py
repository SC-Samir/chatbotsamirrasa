import httpx

from app.domain import FailureReason
from app.domain.value_objects import Region
from app.infrastructure.scalingo.http_client import ScalingoHTTPClient


class DummyTokenProvider:
    def get_token(self) -> str:
        return "token"

    def refresh(self) -> str:
        return "token"


def test_http_404_maps_to_not_found(httpx_mock):
    client = ScalingoHTTPClient(DummyTokenProvider())
    url = "https://api.osc-fr1.scalingo.com/v1/apps/demo"
    httpx_mock.add_response(method="GET", url=url, status_code=404, json={"error": "not found"})

    result = client.request("GET", Region.OSC_FR1, "/v1/apps/demo")

    assert result.success is False
    assert result.error.reason == FailureReason.NOT_FOUND


def test_timeout_maps_to_transient(monkeypatch):
    client = ScalingoHTTPClient(DummyTokenProvider())

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, *args, **kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "Client", FakeClient)

    result = client.request("GET", Region.OSC_FR1, "/v1/apps/demo")

    assert result.success is False
    assert result.error.reason == FailureReason.TRANSIENT
