"""
Celery background tasks for deployment polling and monitoring.

This module contains asynchronous tasks that run in the background to monitor
deployment status and publish updates via Redis Pub/Sub.
"""
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis
from celery import Celery

from app.config import settings
from app.core.logging import StructuredLogger
from app.domain import AppId, DeploymentStatus, Region
from app.infrastructure.scalingo import AppsAPI, ScalingoHTTPClient, build_default_token_provider

celery_app = Celery("tasks", broker=settings.redis_url)

# Client Redis pour Pub/Sub
redis_client = redis.from_url(settings.redis_url)
logger = StructuredLogger("tasks")


# Initialize AppsAPI for direct use
token_provider = build_default_token_provider()
scalingo_http_client = ScalingoHTTPClient(token_provider)
apps_api = AppsAPI(scalingo_http_client)

STATUS_PROGRESS = {
    DeploymentStatus.QUEUED: 10,
    DeploymentStatus.BUILDING: 45,
    DeploymentStatus.PUSHING: 70,
    DeploymentStatus.STARTING: 90,
    DeploymentStatus.SUCCESS: 100,
    DeploymentStatus.CRASHED_ERROR: 100,
    DeploymentStatus.TIMEOUT_ERROR: 100,
    DeploymentStatus.BUILD_ERROR: 100,
    DeploymentStatus.ABORTED: 100,
}

STATUS_LABELS = {
    DeploymentStatus.QUEUED: "Queued",
    DeploymentStatus.BUILDING: "Building image",
    DeploymentStatus.PUSHING: "Pushing image",
    DeploymentStatus.STARTING: "Starting app",
    DeploymentStatus.SUCCESS: "Deployment successful",
    DeploymentStatus.CRASHED_ERROR: "Failed: crashed on start",
    DeploymentStatus.TIMEOUT_ERROR: "Failed: start timeout",
    DeploymentStatus.BUILD_ERROR: "Failed: build error",
    DeploymentStatus.ABORTED: "Deployment aborted",
}


def _publish_to_chat(channel: str, payload: Dict[str, Any]) -> None:
    """Publishes a structured payload on Redis Pub/Sub to be sent to chat."""
    try:
        redis_client.publish(channel, json.dumps(payload))
        logger.debug("Message published to chat channel", channel=channel, payload=payload)
    except Exception as e:
        logger.error("Redis publication error", channel=channel, error=str(e))


def build_deployment_event(
    event_type: str,
    app_name: str,
    deployment_id: str,
    status: str,
    message: str,
    *,
    final: bool = False,
    error_kind: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds a structured deployment event payload."""
    return {
        "type": event_type,
        "deployment_id": deployment_id,
        "app_name": app_name,
        "status": status,
        "phase_label": STATUS_LABELS.get(status, status),
        "progress": STATUS_PROGRESS.get(status, 0),
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final": final,
        "error_kind": error_kind,
    }


@celery_app.task
def poll_deployment_status(app_name: str, region: str, deployment_id: str):
    """Monitors deployment status and publishes structured status updates."""
    channel = f"deployment:{deployment_id}"

    status_messages = {
        DeploymentStatus.QUEUED: f"⏰ Deployment of *{app_name}* queued...",
        DeploymentStatus.BUILDING: f"🔨 Deployment of *{app_name}* building...",
        DeploymentStatus.PUSHING: f"📦 Docker image of *{app_name}* pushing...",
        DeploymentStatus.STARTING: f"🚀 Starting *{app_name}*...",
        DeploymentStatus.SUCCESS: f"✅ Deployment of *{app_name}* successful!",
        DeploymentStatus.CRASHED_ERROR: f"❌ Deployment of *{app_name}* failed: application failed to start. Check logs.",
        DeploymentStatus.TIMEOUT_ERROR: f"⏱️ Deployment of *{app_name}* failed: timeout (app didn't start within 60 seconds).",
        DeploymentStatus.BUILD_ERROR: f"🔥 Deployment of *{app_name}* failed: build error. Check logs.",
        DeploymentStatus.ABORTED: f"⚠️ Deployment of *{app_name}* aborted (connection interrupted).",
    }

    last_status = None
    last_heartbeat_at = 0.0
    heartbeat_interval_seconds = 12.0

    while True:
        # Use AppsAPI directly instead of ScalingoManager
        result = apps_api.get_deployment_status(app_name, region, deployment_id)
        
        if not result.success:
            error_msg = f"❌ Error: Unable to retrieve status for {app_name} (ID: {deployment_id})"
            logger.error(
                "Unable to retrieve deployment status",
                app_name=app_name,
                region=region,
                deployment_id=deployment_id,
                error=str(result.error) if result.error else "unknown error",
            )
            _publish_to_chat(
                channel,
                build_deployment_event(
                    "deployment_finished",
                    app_name,
                    deployment_id,
                    "status-unavailable",
                    error_msg,
                    final=True,
                    error_kind="status_unavailable",
                ),
            )
            break

        deployment_info = result.value
        if not deployment_info:
            error_msg = f"❌ Error: Empty response for {app_name} (ID: {deployment_id})"
            logger.error(
                "Empty deployment status response",
                app_name=app_name,
                region=region,
                deployment_id=deployment_id,
            )
            _publish_to_chat(
                channel,
                build_deployment_event(
                    "deployment_finished",
                    app_name,
                    deployment_id,
                    "status-unavailable",
                    error_msg,
                    final=True,
                    error_kind="status_unavailable",
                ),
            )
            break

        status = deployment_info.get("deployment", {}).get("status")
        logger.info(
            "Deployment status polled",
            app_name=app_name,
            region=region,
            deployment_id=deployment_id,
            status=status,
        )

        message = status_messages.get(status, f"ℹ️ Deployment of *{app_name}*: status {status}")
        is_final = DeploymentStatus.is_final_status(status)

        if status != last_status or is_final:
            event_type = "deployment_finished" if is_final else "deployment_status"
            error_kind = status if DeploymentStatus.is_error_status(status) else None
            _publish_to_chat(
                channel,
                build_deployment_event(
                    event_type,
                    app_name,
                    deployment_id,
                    status,
                    message,
                    final=is_final,
                    error_kind=error_kind,
                ),
            )
            last_status = status
            last_heartbeat_at = time.time()
        elif time.time() - last_heartbeat_at >= heartbeat_interval_seconds:
            _publish_to_chat(
                channel,
                build_deployment_event(
                    "deployment_heartbeat",
                    app_name,
                    deployment_id,
                    status,
                    f"⏳ *{app_name}* still {status}...",
                    final=False,
                ),
            )
            last_heartbeat_at = time.time()

        if is_final:
            break

        time.sleep(settings.deployment_poll_interval)
