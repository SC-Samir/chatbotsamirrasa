import time
import json
import redis
from celery import Celery
from app.config import settings
from app.scalingo_manager import ScalingoManager
from app.models import DeploymentStatus

celery_app = Celery("tasks", broker=settings.redis_url)

# Client Redis pour Pub/Sub
redis_client = redis.from_url(settings.redis_url)

def _publish_to_chat(channel: str, message: str):
    """Publishes a message on Redis Pub/Sub to be sent to chat."""
    try:
        redis_client.publish(channel, json.dumps({"message": message}))
        print(f"📤 Message published on {channel}: {message}")
    except Exception as e:
        print(f"❌ Error during Redis publication: {e}")

@celery_app.task
def poll_deployment_status(app_name: str, region: str, deployment_id: str):
    """Monitors deployment status and publishes final result on Redis Pub/Sub."""
    channel = f"deployment:{deployment_id}"
    scalingo = ScalingoManager()
    
    # Messages for each status
    status_messages = {
        DeploymentStatus.QUEUED: f"⏰ Deployment of *{app_name}* queued...",
        DeploymentStatus.BUILDING: f"🔨 Deployment of *{app_name}* building...",
        DeploymentStatus.PUSHING: f"📦 Docker image of *{app_name}* pushing...",
        DeploymentStatus.STARTING: f"🚀 Starting *{app_name}*...",
        DeploymentStatus.SUCCESS: f"✅ Deployment of *{app_name}* successful!",
        DeploymentStatus.CRASHED_ERROR: f"❌ Deployment of *{app_name}* failed: application failed to start. Check logs.",
        DeploymentStatus.TIMEOUT_ERROR: f"⏱️ Deployment of *{app_name}* failed: timeout (app didn't start within 60 seconds).",
        DeploymentStatus.BUILD_ERROR: f"🔥 Deployment of *{app_name}* failed: build error. Check logs.",
        DeploymentStatus.ABORTED: f"⚠️ Deployment of *{app_name}* aborted (connection interrupted)."
    }
    
    while True:
        deployment_info = scalingo.get_deployment_status(app_name, region, deployment_id)
        if not deployment_info:
            error_msg = f"❌ Error: Unable to retrieve status for {app_name} (ID: {deployment_id})"
            print(error_msg)
            _publish_to_chat(channel, error_msg)
            break

        status = deployment_info["deployment"]["status"]
        print(f"Deployment status for {app_name}: {status}")
        
        # Publish message corresponding to status
        message = status_messages.get(status, f"ℹ️ Deployment of *{app_name}*: status {status}")
        _publish_to_chat(channel, message)
        
        # If it's a final status, stop monitoring
        if DeploymentStatus.is_final_status(status):
            break
        
        # Wait before next check
        time.sleep(settings.deployment_poll_interval)