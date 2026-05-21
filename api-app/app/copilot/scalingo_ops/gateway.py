from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.domain import Region
from app.infrastructure.scalingo.http_client import ScalingoHTTPClient


class ScalingoOpsGateway:
    def __init__(self, client: ScalingoHTTPClient):
        self.client = client

    def _region(self, value: str) -> Region:
        return Region(value)

    def _build_archive_source_url(self, github_repo: str, git_ref: str) -> str:
        repo = github_repo[:-4] if github_repo.endswith(".git") else github_repo
        repo = repo.rstrip("/")
        parsed = urlparse(repo)

        if parsed.netloc.lower() == "github.com":
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2:
                owner, repository = path_parts[0], path_parts[1]
                return f"https://codeload.github.com/{owner}/{repository}/tar.gz/refs/heads/{git_ref}"

        # Fallback that still works for generic GitHub-like hosts.
        return f"{repo}/archive/{git_ref}.tar.gz"

    def apps_list(self, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), "/v1/apps")
        return result.value if result.success and result.value else {"apps": []}

    def apps_get(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}")
        return result.value if result.success and result.value else {}

    def apps_create(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), "/v1/apps", json_payload={"app": {"name": app_name}})
        return result.value if result.success and result.value else {}

    def apps_update(self, app_name: str, region: str, app_patch: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"app": app_patch}
        result = self.client.request(
            "PATCH",
            self._region(region),
            f"/v1/apps/{app_name}",
            params={"current_name": app_name},
            json_payload=payload,
        )
        return result.value if result.success and result.value else {}

    def apps_delete(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}", params={"current_name": app_name})
        return result.value if result.success and result.value else {"accepted": result.success}

    def apps_restart(self, app_name: str, region: str, scope: Optional[list[str]] = None) -> Dict[str, Any]:
        payload = {"scope": scope} if scope else None
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/restart", json_payload=payload)
        return result.value if result.success and result.value else {"accepted": result.success}

    def deployments_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/deployments")
        return result.value if result.success and result.value else {"deployments": []}

    def deployment_details(self, app_name: str, region: str, deployment_id: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/deployments/{deployment_id}")
        return result.value if result.success and result.value else {}

    def deployment_output(self, app_name: str, region: str, deployment_id: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/deployments/{deployment_id}/output")
        return result.value if result.success and result.value else {}

    def deployments_create(self, app_name: str, region: str, source_url: str, github_repo: str, git_ref: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"git_ref": git_ref}
        if source_url:
            payload["source_url"] = source_url
        elif github_repo:
            payload["source_url"] = self._build_archive_source_url(github_repo, git_ref)
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/deployments", json_payload=payload)
        return result.value if result.success and result.value else {}

    def deployments_rollback(self, app_name: str, region: str, release_id: str) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/releases/{release_id}/rollback")
        return result.value if result.success and result.value else {"accepted": result.success}

    def deployment_cache_reset(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/cache")
        return result.value if result.success and result.value else {"accepted": result.success}

    def autoscalers_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/autoscalers")
        return result.value if result.success and result.value else {"autoscalers": []}

    def autoscalers_create(self, app_name: str, region: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/autoscalers", json_payload=payload)
        return result.value if result.success and result.value else {}

    def autoscalers_update(self, app_name: str, region: str, autoscaler_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("PATCH", self._region(region), f"/v1/apps/{app_name}/autoscalers/{autoscaler_id}", json_payload=payload)
        return result.value if result.success and result.value else {}

    def autoscalers_delete(self, app_name: str, region: str, autoscaler_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/autoscalers/{autoscaler_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def domains_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/domains")
        return result.value if result.success and result.value else {"domains": []}

    def domains_create(self, app_name: str, region: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/domains", json_payload=payload)
        return result.value if result.success and result.value else {}

    def domains_delete(self, app_name: str, region: str, domain: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/domains/{domain}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def collaborators_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/collaborators")
        return result.value if result.success and result.value else {"collaborators": []}

    def collaborators_invite(self, app_name: str, region: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/collaborators", json_payload=payload)
        return result.value if result.success and result.value else {}

    def collaborators_update(self, app_name: str, region: str, collaborator_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("PATCH", self._region(region), f"/v1/apps/{app_name}/collaborators/{collaborator_id}", json_payload=payload)
        return result.value if result.success and result.value else {}

    def collaborators_delete(self, app_name: str, region: str, collaborator_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/collaborators/{collaborator_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def events_list(self, app_name: str, region: str, page: Optional[int] = None, per_page: Optional[int] = None, event_type: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if event_type:
            params["type"] = event_type
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/events", params=params or None)
        return result.value if result.success and result.value else {"events": []}

    def one_off_run(self, app_name: str, region: str, command: str, size: Optional[str] = None, detached: Optional[bool] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"command": command}
        if size:
            payload["size"] = size
        if detached is not None:
            payload["detached"] = detached
        if env:
            payload["env"] = env
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/run", json_payload=payload)
        return result.value if result.success and result.value else {}

    def containers_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/ps")
        return result.value if result.success and result.value else {"containers": []}

    def containers_scale(self, app_name: str, region: str, container_type: str, amount: int, size: Optional[str] = None) -> Dict[str, Any]:
        container: Dict[str, Any] = {"name": container_type, "amount": amount}
        if size:
            container["size"] = size
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/scale", json_payload={"containers": [container]})
        return result.value if result.success and result.value else {"accepted": result.success}

    def containers_stop(self, app_name: str, region: str, container_id: str) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/containers/{container_id}/stop")
        return result.value if result.success and result.value else {"accepted": result.success}

    def containers_signal(self, app_name: str, region: str, container_id: str, signal: str) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/containers/{container_id}/kill", json_payload={"signal": signal})
        return result.value if result.success and result.value else {"accepted": result.success}

    def log_drains_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/log_drains")
        return result.value if result.success and result.value else {"drains": []}

    def log_drains_create(self, app_name: str, region: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/log_drains", json_payload=payload)
        return result.value if result.success and result.value else {}

    def log_drains_delete(self, app_name: str, region: str, drain_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/log_drains/{drain_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def notifiers_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/notifiers")
        return result.value if result.success and result.value else {"notifiers": []}

    def notifiers_create(self, app_name: str, region: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/notifiers", json_payload=payload)
        return result.value if result.success and result.value else {}

    def notifiers_update(self, app_name: str, region: str, notifier_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.request("PATCH", self._region(region), f"/v1/apps/{app_name}/notifiers/{notifier_id}", json_payload=payload)
        return result.value if result.success and result.value else {}

    def notifiers_delete(self, app_name: str, region: str, notifier_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/notifiers/{notifier_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def env_vars_list(self, app_name: str, region: str, aliases: bool = True) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/variables", params={"aliases": aliases})
        return result.value if result.success and result.value else {"variables": []}

    def env_vars_set(self, app_name: str, region: str, name: str, value: str) -> Dict[str, Any]:
        payload = {"variable": {"name": name, "value": value}}
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/variables", json_payload=payload)
        return result.value if result.success and result.value else {}

    def env_vars_unset(self, app_name: str, region: str, name: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/variables/{name}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def addons_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/addons")
        return result.value if result.success and result.value else {"addons": []}

    def addons_add(self, app_name: str, region: str, addon_id: str, plan: str = "", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        addon: Dict[str, Any] = {"addon_id": addon_id}
        if plan:
            addon["plan"] = plan
        if options:
            addon["options"] = options
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/addons", json_payload={"addon": addon})
        return result.value if result.success and result.value else {}

    def addons_remove(self, app_name: str, region: str, addon_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/addons/{addon_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def projects_list(self, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), "/v1/projects")
        return result.value if result.success and result.value else {"projects": []}
