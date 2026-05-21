from __future__ import annotations

from types import SimpleNamespace

from app.copilot.scalingo_ops.gateway import ScalingoOpsGateway


class DummyClient:
    def __init__(self) -> None:
        self.calls = []

    def request(self, method, region, path, json_payload=None, params=None):  # noqa: ANN001
        self.calls.append(
            {
                "method": method,
                "region": region,
                "path": path,
                "json_payload": json_payload,
                "params": params,
            }
        )
        return SimpleNamespace(success=True, value={"ok": True})


def test_deployments_create_builds_codeload_source_url_for_github_repo():
    gateway = ScalingoOpsGateway(client=DummyClient())

    gateway.deployments_create(
        app_name="demo",
        region="osc-fr1",
        source_url="",
        github_repo="https://github.com/Scalingo/sample-go-gin",
        git_ref="master",
    )

    assert gateway.client.calls[0]["json_payload"] == {
        "git_ref": "master",
        "source_url": "https://codeload.github.com/Scalingo/sample-go-gin/tar.gz/refs/heads/master",
    }


def test_deployments_create_prefers_explicit_source_url_over_github_repo():
    gateway = ScalingoOpsGateway(client=DummyClient())

    gateway.deployments_create(
        app_name="demo",
        region="osc-fr1",
        source_url="https://example.com/archive.tar.gz",
        github_repo="https://github.com/Scalingo/sample-go-gin",
        git_ref="master",
    )

    assert gateway.client.calls[0]["json_payload"] == {
        "git_ref": "master",
        "source_url": "https://example.com/archive.tar.gz",
    }
