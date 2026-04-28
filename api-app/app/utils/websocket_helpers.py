"""
Utilitaires pour la gestion des WebSockets.
"""
import asyncio
import time
from typing import Optional, Dict, Any
from fastapi import WebSocket
from app.scalingo_manager import ScalingoManager


class WebSocketHelpers:
    """Utilitaires pour les opérations WebSocket."""
    
    def __init__(self, scalingo_manager: ScalingoManager):
        self.scalingo_manager = scalingo_manager
    
    async def send_progress_message(self, websocket: WebSocket, message: str) -> None:
        """Envoie un message de progression."""
        await websocket.send_text(message)
    
    async def wait_with_messages(self, websocket: WebSocket, 
                                check_func, max_wait_time: int = 120, 
                                check_interval: int = 3) -> bool:
        """Attend avec des messages de progression."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            await self.send_progress_message(websocket, "🔍 Status check...")
            
            result = await check_func()
            if result:
                return True
            
            if time.time() - start_time < max_wait_time:
                await self.send_progress_message(websocket, f"⏳ Waiting {check_interval}s before next check...")
                await asyncio.sleep(check_interval)
        
        return False
    
    async def check_app_status(self, websocket: WebSocket, app_name: str, region: str) -> bool:
        """Vérifie le statut de l'application."""
        app_info = self.scalingo_manager.get_app_status(app_name, region)
        
        if not app_info:
            await self.send_progress_message(websocket, "❌ Unable to retrieve application status")
            return False
        
        app_data = app_info.get("app", {})
        status = app_data.get("status")
        
        if status == "running":
            # Vérifier aussi les conteneurs
            containers_info = self.scalingo_manager.get_containers_status(app_name, region)
            if containers_info:
                containers = containers_info.get("containers", [])
                running_containers = len([c for c in containers if c.get("state") == "running"])
                if running_containers > 0:
                    await self.send_progress_message(websocket, f"✅ Application is running with {running_containers} containers!")
                    return True
                else:
                    await self.send_progress_message(websocket, "⚠️ App is 'running' but no containers are running...")
            else:
                await self.send_progress_message(websocket, "✅ Application is 'running'")
                return True
        else:
            await self.send_progress_message(websocket, f"⚠️ Status: {status}")
        
        return False
    
    async def check_scaling_status(self, websocket: WebSocket, app_name: str, region: str, 
                                  container_name: str, target_amount: int) -> bool:
        """Vérifie le statut de scaling."""
        containers_info = self.scalingo_manager.get_containers_status(app_name, region)
        
        if not containers_info:
            await self.send_progress_message(websocket, "❌ Unable to retrieve container status")
            return False
        
        containers = containers_info.get("containers", [])
        target_containers = [c for c in containers if c.get("type") == container_name]
        running_count = len([c for c in target_containers if c.get("state") == "running"])
        
        if running_count == target_amount:
            await self.send_progress_message(websocket, f"🎉 All {target_amount} containers are running!")
            return True
        
        # Afficher le statut actuel
        await self.send_progress_message(websocket, f"📊 Container status for *{container_name}*:")
        for i, container in enumerate(target_containers):
            label = container.get("label", f"{container_name}-{i+1}")
            state = container.get("state", "unknown")
            size_info = container.get("container_size", {})
            size = size_info.get("name", "unknown") if size_info else "unknown"
            command = container.get("command", "")[:50] + "..." if len(container.get("command", "")) > 50 else container.get("command", "")
            await self.send_progress_message(websocket, f"  • {label}: {state} ({size}) - {command}")
        
        return False
