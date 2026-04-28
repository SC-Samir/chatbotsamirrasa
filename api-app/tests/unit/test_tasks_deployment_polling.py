from app.tasks import poll_deployment_status


def test_poll_deployment_status_deduplicates_consecutive_statuses(monkeypatch):
    statuses = ["building", "building", "building", "success"]

    class FakeScalingo:
        def __init__(self):
            self.idx = 0

        def get_deployment_status(self, app_name, region, deployment_id):
            status = statuses[self.idx]
            self.idx += 1
            return {"deployment": {"status": status}}

    published = []

    monkeypatch.setattr("app.tasks.ScalingoManager", FakeScalingo)
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

    class FakeScalingo:
        def __init__(self):
            self.idx = 0

        def get_deployment_status(self, app_name, region, deployment_id):
            status = statuses[self.idx]
            self.idx += 1
            return {"deployment": {"status": status}}

    published = []

    monkeypatch.setattr("app.tasks.ScalingoManager", FakeScalingo)
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

    class FakeScalingo:
        def __init__(self):
            self.calls = 0

        def get_deployment_status(self, app_name, region, deployment_id):
            self.calls += 1
            return {"deployment": {"status": statuses[0]}}

    published = []
    fake_scalingo = FakeScalingo()

    monkeypatch.setattr("app.tasks.ScalingoManager", lambda: fake_scalingo)
    monkeypatch.setattr("app.tasks._publish_to_chat", lambda channel, payload: published.append(payload))
    monkeypatch.setattr("app.tasks.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("app.tasks.settings.deployment_poll_interval", 0)

    poll_deployment_status("demo-app", "osc-fr1", "dep-3")

    assert fake_scalingo.calls == 1
    assert len(published) == 1
    assert published[0]["type"] == "deployment_finished"
    assert published[0]["final"] is True
