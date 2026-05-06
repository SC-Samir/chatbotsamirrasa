from __future__ import annotations

from dataclasses import dataclass

from app.copilot.contracts import CommandContext
from app.copilot.orchestration.engine import CommandEngine


@dataclass
class DummyGateway:
    def apps_list(self, region: str):
        return {"apps": [{"name": "a1", "region": region}]}

    def apps_get(self, app_name: str, region: str):
        return {"app": {"name": app_name, "region": region}}

    def apps_update(self, app_name: str, region: str, app_patch: dict):
        return {"app": {"name": app_name, "region": region, **app_patch}}

    def deployments_list(self, app_name: str, region: str):
        return {"deployments": [{"id": "d1", "app": app_name, "region": region}]}

    def deployment_details(self, app_name: str, region: str, deployment_id: str):
        return {"deployment": {"id": deployment_id}}

    def deployment_output(self, app_name: str, region: str, deployment_id: str):
        return {"output": f"log-{deployment_id}"}

    def deployment_cache_reset(self, app_name: str, region: str):
        return {"accepted": True}

    def autoscalers_list(self, app_name: str, region: str):
        return {"autoscalers": []}

    def autoscalers_create(self, app_name: str, region: str, payload: dict):
        return payload

    def autoscalers_update(self, app_name: str, region: str, autoscaler_id: str, payload: dict):
        return {"id": autoscaler_id, **payload}

    def autoscalers_delete(self, app_name: str, region: str, autoscaler_id: str):
        return {"accepted": True, "autoscaler_id": autoscaler_id}

    def events_list(self, app_name: str, region: str):
        return {"events": []}

    def domains_list(self, app_name: str, region: str):
        return {"domains": []}

    def domains_create(self, app_name: str, region: str, payload: dict):
        return payload

    def domains_delete(self, app_name: str, region: str, domain: str):
        return {"accepted": True, "domain": domain}

    def collaborators_list(self, app_name: str, region: str):
        return {"collaborators": []}

    def collaborators_invite(self, app_name: str, region: str, payload: dict):
        return payload

    def collaborators_update(self, app_name: str, region: str, collaborator_id: str, payload: dict):
        return {"id": collaborator_id, **payload}

    def collaborators_delete(self, app_name: str, region: str, collaborator_id: str):
        return {"accepted": True, "collaborator_id": collaborator_id}

    def log_drains_list(self, app_name: str, region: str):
        return {"drains": []}

    def log_drains_create(self, app_name: str, region: str, payload: dict):
        return payload

    def log_drains_delete(self, app_name: str, region: str, drain_id: str):
        return {"accepted": True, "drain_id": drain_id}

    def notifiers_list(self, app_name: str, region: str):
        return {"notifiers": []}

    def notifiers_create(self, app_name: str, region: str, payload: dict):
        return payload

    def notifiers_update(self, app_name: str, region: str, notifier_id: str, payload: dict):
        return {"id": notifier_id, **payload}

    def notifiers_delete(self, app_name: str, region: str, notifier_id: str):
        return {"accepted": True, "notifier_id": notifier_id}

    def one_off_run(self, app_name: str, region: str, command: str, size=None, detached=None, env=None):
        return {"one_off": {"command": command, "size": size, "detached": detached, "env": env}}

    def containers_stop(self, app_name: str, region: str, container_id: str):
        return {"accepted": True, "container_id": container_id}

    def containers_signal(self, app_name: str, region: str, container_id: str, signal: str):
        return {"accepted": True, "container_id": container_id, "signal": signal}

    def projects_list(self, region: str):
        return {"projects": [{"id": "p1", "region": region}]}


class DummyMemory:
    def __init__(self):
        self.tokens = {}

    def snapshot(self, user_id: str, session_id: str):
        class Snap:
            session = {"entities": {"app_name": "my-app", "region": "osc-fr1"}}
            facts = {}

        return Snap()

    def issue_confirmation_token(self, session_id: str, command: str, payload: dict, ttl_seconds: int = 120):
        token = "abcd"
        self.tokens[token] = {"command": command, "payload": payload}
        return token

    def consume_confirmation_token(self, session_id: str, token: str):
        return self.tokens.pop(token, None)

    def forget(self, user_id: str, key: str):
        return True

    def pin(self, user_id: str, key: str):
        return True


def _ctx() -> CommandContext:
    return CommandContext(
        session_id="s1",
        user_id="u1",
        app_scope=None,
        region_scope=None,
        trace_id="t1",
    )


def test_deployments_list_uses_scoped_entities():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute("deployments.list", {}, "list deployments", _ctx())
    assert result.status == "success"
    assert result.event_type == "deployments.list"
    assert result.structured_payload["deployments"][0]["app"] == "my-app"


def test_risky_action_requires_confirmation_token():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute("domains.delete", {"domain": "x.example.com"}, "delete domain", _ctx())
    assert result.status == "requires_confirmation"
    assert result.structured_payload["confirm_token"] == "abcd"


def test_confirm_executes_pending_risky_action():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    _ = engine.execute("domains.delete", {"domain": "x.example.com"}, "delete domain", _ctx())
    result = engine.execute("confirm", {"confirm_token": "abcd"}, "confirm abcd", _ctx())
    assert result.status == "success"
    assert result.event_type == "domains.delete"


def test_apps_list_requires_region():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute("apps.list", {}, "list apps", _ctx())
    assert result.status == "warning"
    assert result.event_type == "command.validation_error"


def test_apps_list_success():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute("apps.list", {"region": "osc-fr1"}, "list apps", _ctx())
    assert result.status == "success"
    assert result.event_type == "apps.list"


def test_apps_set_force_https_is_confirmed():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute(
        "apps.set_force_https",
        {"app_name": "my-app", "region": "osc-fr1", "enabled": True},
        "set force https",
        _ctx(),
    )
    assert result.status == "requires_confirmation"
