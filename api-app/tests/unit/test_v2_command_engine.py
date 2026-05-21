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

    def apps_create(self, app_name: str, region: str):
        return {"app": {"name": app_name, "region": region}}

    def apps_restart(self, app_name: str, region: str, scope=None):
        return {"accepted": True, "scope": scope}

    def apps_update(self, app_name: str, region: str, app_patch: dict):
        return {"app": {"name": app_name, "region": region, **app_patch}}

    def deployments_list(self, app_name: str, region: str):
        return {"deployments": [{"id": "d1", "app": app_name, "region": region}]}

    def deployment_details(self, app_name: str, region: str, deployment_id: str):
        return {"deployment": {"id": deployment_id}}

    def deployment_output(self, app_name: str, region: str, deployment_id: str):
        return {"output": f"log-{deployment_id}"}

    def deployments_create(self, app_name: str, region: str, source_url: str, github_repo: str, git_ref: str):
        return {"deployment": {"source_url": source_url, "github_repo": github_repo, "git_ref": git_ref}}

    def deployments_rollback(self, app_name: str, region: str, release_id: str):
        return {"accepted": True, "release_id": release_id}

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

    def events_list(self, app_name: str, region: str, page=None, per_page=None, event_type=None):
        return {"events": [], "page": page, "per_page": per_page, "type": event_type}

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

    def containers_list(self, app_name: str, region: str):
        return {"containers": []}

    def containers_scale(self, app_name: str, region: str, container_type: str, amount: int, size=None):
        return {"accepted": True, "container_type": container_type, "amount": amount, "size": size}

    def containers_stop(self, app_name: str, region: str, container_id: str):
        return {"accepted": True, "container_id": container_id}

    def containers_signal(self, app_name: str, region: str, container_id: str, signal: str):
        return {"accepted": True, "container_id": container_id, "signal": signal}

    def projects_list(self, region: str):
        return {"projects": [{"id": "p1", "region": region}]}

    def env_vars_list(self, app_name: str, region: str, aliases=True):
        return {"variables": [{"name": "A", "value": "1"}], "aliases": aliases}

    def env_vars_set(self, app_name: str, region: str, name: str, value: str):
        return {"variable": {"name": name, "value": value}}

    def env_vars_unset(self, app_name: str, region: str, name: str):
        return {"accepted": True, "name": name}

    def addons_list(self, app_name: str, region: str):
        return {"addons": []}

    def addons_add(self, app_name: str, region: str, addon_id: str, plan="", options=None):
        return {"addon": {"id": addon_id, "plan": plan, "options": options or {}}}

    def addons_remove(self, app_name: str, region: str, addon_id: str):
        return {"accepted": True, "addon_id": addon_id}


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


def test_destructive_action_requires_confirmation_token():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute("domains.delete", {"domain": "x.example.com"}, "delete domain", _ctx())
    assert result.status == "requires_confirmation"
    assert result.structured_payload["confirm_token"] == "abcd"


def test_non_destructive_mutation_executes_without_confirmation():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute(
        "apps.set_force_https",
        {"app_name": "my-app", "region": "osc-fr1", "enabled": True},
        "set force https",
        _ctx(),
    )
    assert result.status == "success"
    assert "Action preview:" in result.human_message


def test_confirm_executes_pending_destructive_action():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    _ = engine.execute("domains.delete", {"domain": "x.example.com"}, "delete domain", _ctx())
    result = engine.execute("confirm", {"confirm_token": "abcd"}, "confirm abcd", _ctx())
    assert result.status == "success"
    assert result.event_type == "domains.delete"


def test_apps_delete_returns_error_when_gateway_rejects_deletion():
    class RejectDeleteGateway(DummyGateway):
        def apps_delete(self, app_name: str, region: str):  # noqa: ANN001
            return {"accepted": False}

    engine = CommandEngine(gateway=RejectDeleteGateway(), memory=DummyMemory())
    result = engine.execute(
        "apps.delete",
        {"app_name": "my-app", "region": "osc-fr1", "confirm_token": "tok"},
        "delete app",
        _ctx(),
    )
    assert result.status == "error"
    assert result.event_type == "apps.delete"


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


def test_env_var_set_includes_preview_payload():
    engine = CommandEngine(gateway=DummyGateway(), memory=DummyMemory())
    result = engine.execute(
        "env_vars.set",
        {"app_name": "my-app", "region": "osc-fr1", "env_name": "FOO", "env_value": "bar"},
        "set env",
        _ctx(),
    )
    assert result.status == "success"
    assert "preview" in result.structured_payload
