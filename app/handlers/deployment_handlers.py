"""
Handlers pour les intents de déploiement.
"""
from typing import Dict, Any, Optional
from fastapi import WebSocket
from app.models import AppContext, IntentResponse
from app.handlers.base_handler import BaseHandler
from app.services.deployment_service import DeploymentService
from app.utils.websocket_helpers import WebSocketHelpers


class DeployHandler(BaseHandler):
    """Handler pour l'intent 'deploy'."""
    
    def __init__(self, deployment_service: DeploymentService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.deployment_service = deployment_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "deploy":
            return False
        
        # Validation commune
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region", "github_repo"],
            "To deploy, I need the app name, region and GitHub repo."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        github_repo = params["github_repo"]
        git_ref = params.get("git_ref", "master")
        
        # Message de confirmation
        git_ref_msg = f" (ref: {git_ref})" if git_ref != "master" else ""
        await websocket.send_text(f"✅ Understood! Launching deployment of *{app_name}* to *{region}*{git_ref_msg}...")
        
        # Déclenchement du déploiement
        deployment = self.deployment_service.trigger_deployment(app_name, region, github_repo, git_ref)
        
        if deployment:
            deployment_id = deployment["deployment"]["id"]
            await websocket.send_text(f"Deployment initiated (ID: {deployment_id}). Monitoring in background...")
            
            # Lancement de la tâche Celery
            from app.tasks import poll_deployment_status
            poll_deployment_status.delay(app_name, region, deployment_id)
            
            return {"handled": True, "deployment_id": deployment_id}
        else:
            await self._send_error_message(websocket, "Error during deployment launch.")
            return True


class CreateAndDeployHandler(BaseHandler):
    """Handler pour l'intent 'create_and_deploy'."""
    
    def __init__(self, deployment_service: DeploymentService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.deployment_service = deployment_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "create_and_deploy":
            return False
        
        # Validation commune
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region", "github_repo"],
            "To create and deploy, I need the app name, region and GitHub repo."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        github_repo = params["github_repo"]
        git_ref = params.get("git_ref", "master")
        
        # Création de l'application
        git_ref_msg = f" (ref: {git_ref})" if git_ref != "master" else ""
        await websocket.send_text(f"🚀 Starting creation process for *{app_name}*{git_ref_msg}...")
        
        new_app = self.deployment_service.create_app(app_name, region)
        if not new_app:
            await self._send_error_message(websocket, "Application creation failed. The name might already be taken.")
            return True
        
        await self._send_success_message(websocket, "Application created! Triggering first deployment...")
        
        # Déploiement
        deployment = self.deployment_service.trigger_deployment(app_name, region, github_repo, git_ref)
        
        if deployment:
            deployment_id = deployment["deployment"]["id"]
            await websocket.send_text(f"Deployment initiated (ID: {deployment_id}). Monitoring in background...")
            
            # Lancement de la tâche Celery
            from app.tasks import poll_deployment_status
            poll_deployment_status.delay(app_name, region, deployment_id)
            
            return {"handled": True, "deployment_id": deployment_id}
        else:
            await self._send_error_message(websocket, "Error during deployment launch.")
            return True
