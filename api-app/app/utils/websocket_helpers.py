"""Utilities for WebSocket progress and polling helpers."""
import asyncio
import time
from typing import Any, Dict

from fastapi import WebSocket

from app.domain import AppId, Region
from app.infrastructure.scalingo import AppsAPI


class WebSocketHelpers:
    """Utilities for WebSocket operations."""

    def __init__(self, apps_api: AppsAPI):
        self.apps_api = apps_api

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
        result = self.apps_api.get_app_status(AppId(app_name), Region(region))
        if not result.success:
            await self.send_progress_message(websocket, "❌ Unable to retrieve application status")
            return False

        status = result.value.status
        if status == "running":
            containers_result = self.apps_api.get_containers_status(AppId(app_name), Region(region))
            if containers_result.success:
                running_containers = len([c for c in containers_result.value if c.state == "running"])
                if running_containers > 0:
                    await self.send_progress_message(
                        websocket, f"✅ Application is running with {running_containers} containers!"
                    )
                    return True
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
        result = self.apps_api.get_containers_status(AppId(app_name), Region(region))
        if not result.success:
            await self.send_progress_message(websocket, "❌ Unable to retrieve container status")
            return False

        target_containers = [c for c in result.value if c.type == container_name]
        running_count = len([c for c in target_containers if c.state == "running"])
        
        if running_count == target_amount:
            await self.send_progress_message(websocket, f"🎉 All {target_amount} containers are running!")
            return True
        
        # Afficher le statut actuel
        await self.send_progress_message(websocket, f"📊 Container status for *{container_name}*:")
        for i, container in enumerate(target_containers):
            label = container.label or f"{container_name}-{i+1}"
            state = container.state
            size = container.size or "unknown"
            command = container.command or ""
            command = command[:50] + "..." if len(command) > 50 else command
            await self.send_progress_message(websocket, f"  • {label}: {state} ({size}) - {command}")
        
        return False
