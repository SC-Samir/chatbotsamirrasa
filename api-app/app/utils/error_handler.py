"""
Gestionnaire d'erreurs centralisé.
"""
import traceback
from typing import Optional, Dict, Any
from fastapi import WebSocket
from app.exceptions.handler_exceptions import (
    HandlerException, ValidationException, DeploymentException, 
    ScalingException, AppManagementException
)
from app.core.logging import StructuredLogger

logger = StructuredLogger("error_handler")


class ErrorHandler:
    """Gestionnaire d'erreurs centralisé."""
    
    @staticmethod
    async def handle_validation_error(websocket: WebSocket, error: ValidationException) -> None:
        """Gère les erreurs de validation."""
        missing_fields = ", ".join(error.missing_fields) if error.missing_fields else "required fields"
        await websocket.send_text(f"😕 {error.message} Missing: {missing_fields}")
        logger.warning("Validation error", error=str(error), missing_fields=error.missing_fields)
    
    @staticmethod
    async def handle_deployment_error(websocket: WebSocket, error: DeploymentException) -> None:
        """Gère les erreurs de déploiement."""
        await websocket.send_text(f"❌ Deployment error: {error.message}")
        if error.deployment_id:
            await websocket.send_text(f"Deployment ID: {error.deployment_id}")
        logger.error("Deployment error", 
                    app_name=error.app_name, 
                    region=error.region, 
                    deployment_id=error.deployment_id,
                    error=str(error))
    
    @staticmethod
    async def handle_scaling_error(websocket: WebSocket, error: ScalingException) -> None:
        """Gère les erreurs de scaling."""
        await websocket.send_text(f"❌ Scaling error: {error.message}")
        await websocket.send_text(f"Target: {error.container_name} → {error.target_amount}")
        
        if error.error_type == "scaling_in_progress":
            await websocket.send_text("⚠️ Application is already scaling!")
            await websocket.send_text("🔄 Another scaling operation is in progress. Please wait for it to complete.")
        elif error.error_type == "validation_error":
            await websocket.send_text("❌ Scaling request validation failed.")
        
        logger.error("Scaling error", 
                    app_name=error.app_name, 
                    region=error.region, 
                    container_name=error.container_name,
                    target_amount=error.target_amount,
                    error_type=error.error_type,
                    error=str(error))
    
    @staticmethod
    async def handle_app_management_error(websocket: WebSocket, error: AppManagementException) -> None:
        """Gère les erreurs de gestion d'application."""
        await websocket.send_text(f"❌ {error.operation.title()} error: {error.message}")
        
        if error.operation == "delete":
            await websocket.send_text("🔍 Possible causes:")
            await websocket.send_text("  • Application doesn't exist")
            await websocket.send_text("  • Invalid region")
            await websocket.send_text("  • Insufficient permissions")
            await websocket.send_text("  • Authentication issue")
        elif error.operation == "restart":
            await websocket.send_text("🔍 Possible causes:")
            await websocket.send_text("  • Application doesn't exist")
            await websocket.send_text("  • Application is not in 'running' state")
            await websocket.send_text("  • Invalid region")
        
        logger.error("App management error", 
                    app_name=error.app_name, 
                    region=error.region, 
                    operation=error.operation,
                    error=str(error))
    
    @staticmethod
    async def handle_generic_error(websocket: WebSocket, error: Exception, context: str = "") -> None:
        """Gère les erreurs génériques."""
        await websocket.send_text(f"❌ Unexpected error: {str(error)}")
        if context:
            await websocket.send_text(f"Context: {context}")
        
        logger.error("Generic error", 
                    error=str(error), 
                    context=context,
                    traceback=traceback.format_exc())
    
    @staticmethod
    async def handle_handler_exception(websocket: WebSocket, error: HandlerException) -> None:
        """Gère les exceptions spécifiques aux handlers."""
        if isinstance(error, ValidationException):
            await ErrorHandler.handle_validation_error(websocket, error)
        elif isinstance(error, DeploymentException):
            await ErrorHandler.handle_deployment_error(websocket, error)
        elif isinstance(error, ScalingException):
            await ErrorHandler.handle_scaling_error(websocket, error)
        elif isinstance(error, AppManagementException):
            await ErrorHandler.handle_app_management_error(websocket, error)
        else:
            await ErrorHandler.handle_generic_error(websocket, error, "Handler exception")
