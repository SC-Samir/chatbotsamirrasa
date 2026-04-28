"""
Service de gestion des logs Scalingo.
"""
import asyncio
import httpx
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import WebSocket
from app.scalingo_manager import ScalingoManager
from app.models import LogsRequest, LogsResponse, Region
from app.config import settings
from app.core.logging import StructuredLogger

logger = StructuredLogger("logs_service")


class LogsService:
    """Service pour la gestion des logs."""
    
    def __init__(self, scalingo_manager: ScalingoManager):
        self.scalingo_manager = scalingo_manager
    
    async def get_logs_info(self, request: LogsRequest) -> Optional[LogsResponse]:
        """Récupère les informations des logs."""
        logs_info = self.scalingo_manager.get_logs(
            request.app_name, 
            request.region, 
            n=request.n, 
            filter_param=request.filter_param, 
            stream=request.stream
        )
        
        if not logs_info:
            return None
            
        return LogsResponse(
            logs_url=logs_info["logs_url"],
            parameters=logs_info["parameters"],
            stream=logs_info["stream"],
            app_name=logs_info["app_name"],
            region=logs_info["region"]
        )
    
    async def fetch_and_display_logs(
        self, 
        websocket: WebSocket, 
        logs_url: str, 
        stream_mode: bool = False
    ) -> None:
        """Récupère et affiche les logs statiques ou en streaming."""
        try:
            if not self._validate_logs_url(logs_url):
                await websocket.send_text("❌ URL des logs invalide.")
                return
            logger.info("Fetching logs", logs_url=logs_url, stream_mode=stream_mode)
            
            if stream_mode:
                await self._handle_streaming_logs(websocket, logs_url)
            else:
                await self._handle_static_logs(websocket, logs_url)
                
        except httpx.TimeoutException:
            await websocket.send_text("⏰ Timeout lors de la récupération des logs.")
        except httpx.HTTPStatusError as e:
            await websocket.send_text(f"❌ Erreur HTTP {e.response.status_code} lors de la récupération des logs.")
        except Exception as e:
            await websocket.send_text(f"❌ Erreur lors de la récupération des logs: {str(e)}")
    
    def _validate_logs_url(self, logs_url: str) -> bool:
        """Valide l'URL des logs."""
        return logs_url and logs_url.startswith(('http://', 'https://'))
    
    async def _handle_streaming_logs(self, websocket: WebSocket, logs_url: str) -> None:
        """Gère le streaming des logs."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", logs_url) as response:
                logger.debug("Streaming logs response", status_code=response.status_code)
                response.raise_for_status()
                
                await websocket.send_text("✅ Connexion établie. Streaming des logs en temps réel...")
                await websocket.send_text("─" * 50)
                
                line_count = 0
                async for line in response.aiter_lines():
                    if line.strip():
                        line_count += 1
                        await websocket.send_text(line)
                        
                        if line_count % settings.log_status_interval == 0:
                            await websocket.send_text(f"📊 {line_count} lignes reçues...")
                
                await websocket.send_text("─" * 50)
                await websocket.send_text(f"✅ Stream terminé ({line_count} lignes reçues)")
    
    async def _handle_static_logs(self, websocket: WebSocket, logs_url: str) -> None:
        """Gère les logs statiques."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(logs_url)
            logger.debug("Static logs response", status_code=response.status_code)
            response.raise_for_status()
        
        logs_content = response.text
        
        if not logs_content.strip():
            await websocket.send_text("📭 Aucun log trouvé pour cette application.")
            return
        
        log_lines = logs_content.strip().split('\n')
        total_lines = len(log_lines)
        
        await websocket.send_text(f"📊 {total_lines} lignes de logs récupérées :")
        await websocket.send_text("─" * 50)
        
        # Afficher les logs par chunks
        for i in range(0, len(log_lines), settings.log_chunk_size):
            chunk = log_lines[i:i + settings.log_chunk_size]
            chunk_text = '\n'.join(chunk)
            await websocket.send_text(chunk_text)
            
            if i + settings.log_chunk_size < len(log_lines):
                await asyncio.sleep(0.1)
        
        await websocket.send_text("─" * 50)
        await websocket.send_text(f"✅ Fin des logs ({total_lines} lignes)")
    
    async def stream_logs_to_websocket(self, websocket: WebSocket, logs_url: str) -> None:
        """Stream les logs en temps réel vers le WebSocket."""
        try:
            if not self._validate_logs_url(logs_url):
                await websocket.send_text("❌ URL des logs invalide.")
                return
                
            await websocket.send_text("🔄 Connexion au stream de logs...")
            logger.info("Streaming logs", logs_url=logs_url)
            
            headers = {
                "Upgrade": "websocket",
                "Connection": "Upgrade"
            }
            
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", logs_url, headers=headers) as response:
                    logger.debug("Streaming logs (websocket headers) response", status_code=response.status_code)
                    if response.status_code == 400:
                        await websocket.send_text("⚠️ L'API ne supporte pas le streaming WebSocket pour cette app.")
                        return
                    response.raise_for_status()
                    
                    await websocket.send_text("✅ Connexion établie. Streaming des logs en temps réel...")
                    await websocket.send_text("─" * 50)
                    
                    line_count = 0
                    async for line in response.aiter_lines():
                        if line.strip():
                            line_count += 1
                            await websocket.send_text(line)
                            
                            if line_count % settings.log_status_interval == 0:
                                await websocket.send_text(f"📊 {line_count} lignes reçues...")
                    
                    await websocket.send_text("─" * 50)
                    await websocket.send_text(f"✅ Stream terminé ({line_count} lignes reçues)")
                    
        except httpx.TimeoutException:
            await websocket.send_text("⏰ Timeout lors du streaming des logs.")
        except httpx.HTTPStatusError as e:
            await websocket.send_text(f"❌ Erreur HTTP {e.response.status_code} lors du streaming des logs.")
        except Exception as e:
            await websocket.send_text(f"❌ Erreur lors du streaming des logs: {str(e)}")
