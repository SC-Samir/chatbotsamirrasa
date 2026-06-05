from app.domain import OperationResult
from app.tasks import poll_deployment_status


class FakeAppsAPI:
    """Mock AppsAPI for testing."""
    
    def __init__(self, statuses=None):
        self.statuses = statuses or []
        self.call_count = 0
    
    def get_deployment_status(self, app_name, region, deployment_id):
        if self.call_count < len(self.statuses):
            status = self.statuses[self.call_count]
            self.call_count += 1
            return OperationResult.ok({"deployment": {"status": status}})
        return OperationResult.ok({"deployment": {"status": "success"}})


def test_poll_deployment_status_deduplicates_consecutive_statuses(monkeypatch):
    statuses = ["building", "building", "building", "success"]

    published = []

    fake_apps_api = FakeAppsAPI(statuses)
    monkeypatch.setattr("app.tasks.apps_api", fake_apps_api)
    monkeypatch.setattr("app.tasks._publish_to_chat", lambda channel, payload: published.append(payload))
    monkeypatch.setattr("app.tasks.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("app.tasks.settings.deployment_poll_interval", 0)

    poll_deployment_status("demo-app", "osc-fr1", "dep-1")

    event_types = [evt["type"] for evt in published]
    statuses_seen = [evt["status"] for evt in published]

    assert event_types == ["deployment_status", "deployment_finished"]
    assert statuses_seen == ["building", "success"]


def test_poll_deployment_status_publishes_status_change(monkeypatch):
    statuses = ["queued", "building", "success"]

    published = []

    fake_apps_api = FakeAppsAPI(statuses)
    monkeypatch.setattr("app.tasks.apps_api", fake_apps_api)
    monkeypatch.setattr("app.tasks._publish_to_chat", lambda channel, payload: published.append(payload))
    monkeypatch.setattr("app.tasks.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("app.tasks.settings.deployment_poll_interval", 0)

    poll_deployment_status("demo-app", "osc-fr1", "dep-2")

    assert [evt["status"] for evt in published] == ["queued", "building", "success"]
    assert [evt["type"] for evt in published] == [
        "deployment_status",
        "deployment_status",
        "deployment_finished",
    ]


def test_poll_deployment_status_stops_on_final_status_once(monkeypatch):
    statuses = ["success"]

    published = []
    fake_apps_api = FakeAppsAPI(statuses)

    monkeypatch.setattr("app.tasks.apps_api", fake_apps_api)
    monkeypatch.setattr("app.tasks._publish_to_chat", lambda channel, payload: published.append(payload))
    monkeypatch.setattr("app.tasks.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("app.tasks.settings.deployment_poll_interval", 0)

    poll_deployment_status("demo-app", "osc-fr1", "dep-3")

    assert fake_apps_api.call_count == 1
    assert len(published) == 1
    assert published[0]["type"] == "deployment_finished"
    assert published[0]["final"] is True
