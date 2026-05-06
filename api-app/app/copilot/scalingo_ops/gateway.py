from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain import Region
from app.infrastructure.scalingo.http_client import ScalingoHTTPClient


class ScalingoOpsGateway:
    def __init__(self, client: ScalingoHTTPClient):
        self.client = client

    def _region(self, value: str) -> Region:
        return Region(value)

    def apps_list(self, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), "/v1/apps")
        return result.value if result.success and result.value else {"apps": []}

    def apps_get(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}")
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

    def deployments_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/deployments")
        return result.value if result.success and result.value else {"deployments": []}

    def deployment_details(self, app_name: str, region: str, deployment_id: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/deployments/{deployment_id}")
        return result.value if result.success and result.value else {}

    def deployment_output(self, app_name: str, region: str, deployment_id: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/deployments/{deployment_id}/output")
        return result.value if result.success and result.value else {}

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
        result = self.client.request(
            "PATCH",
            self._region(region),
            f"/v1/apps/{app_name}/collaborators/{collaborator_id}",
            json_payload=payload,
        )
        return result.value if result.success and result.value else {}

    def collaborators_delete(self, app_name: str, region: str, collaborator_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/collaborators/{collaborator_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def events_list(self, app_name: str, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), f"/v1/apps/{app_name}/events")
        return result.value if result.success and result.value else {"events": []}

    def one_off_run(
        self,
        app_name: str,
        region: str,
        command: str,
        size: Optional[str] = None,
        detached: Optional[bool] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"command": command}
        if size:
            payload["size"] = size
        if detached is not None:
            payload["detached"] = detached
        if env:
            payload["env"] = env
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/run", json_payload=payload)
        return result.value if result.success and result.value else {}

    def containers_stop(self, app_name: str, region: str, container_id: str) -> Dict[str, Any]:
        result = self.client.request("POST", self._region(region), f"/v1/apps/{app_name}/containers/{container_id}/stop")
        return result.value if result.success and result.value else {"accepted": result.success}

    def containers_signal(self, app_name: str, region: str, container_id: str, signal: str) -> Dict[str, Any]:
        payload = {"signal": signal}
        result = self.client.request(
            "POST",
            self._region(region),
            f"/v1/apps/{app_name}/containers/{container_id}/kill",
            json_payload=payload,
        )
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
        result = self.client.request(
            "PATCH",
            self._region(region),
            f"/v1/apps/{app_name}/notifiers/{notifier_id}",
            json_payload=payload,
        )
        return result.value if result.success and result.value else {}

    def notifiers_delete(self, app_name: str, region: str, notifier_id: str) -> Dict[str, Any]:
        result = self.client.request("DELETE", self._region(region), f"/v1/apps/{app_name}/notifiers/{notifier_id}")
        return result.value if result.success and result.value else {"accepted": result.success}

    def projects_list(self, region: str) -> Dict[str, Any]:
        result = self.client.request("GET", self._region(region), "/v1/projects")
        return result.value if result.success and result.value else {"projects": []}
