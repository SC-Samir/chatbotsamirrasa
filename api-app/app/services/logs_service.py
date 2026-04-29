from __future__ import annotations

import asyncio
from typing import Optional

import httpx
from fastapi import WebSocket

from app.config import settings
from app.core.logging import StructuredLogger
from app.infrastructure.scalingo import AppsAPI
from app.models import LogsRequest, LogsResponse

logger = StructuredLogger("logs_service")


class LogsService:
    """Logs service with shared HTTP client and typed gateway."""

    def __init__(self, apps_api: AppsAPI, http_client: httpx.AsyncClient):
        self.apps_api = apps_api
        self.http_client = http_client

    async def get_logs_info(self, request: LogsRequest) -> Optional[LogsResponse]:
        result = self.apps_api.get_logs(
            request.app_name,
            request.region,
            n=request.n,
            filter_param=request.filter_param,
            stream=request.stream,
        )
        if not result.success:
            logger.warning(
                "Failed to build logs URL",
                app_name=request.app_name,
                region=str(request.region),
                reason=result.error.reason.value if result.error else "unknown",
            )
            return None

        logs_info = result.value
        return LogsResponse(
            logs_url=logs_info["logs_url"],
            parameters=logs_info["parameters"],
            stream=logs_info["stream"],
            app_name=logs_info["app_name"],
            region=logs_info["region"],
        )

    async def fetch_and_display_logs(self, websocket: WebSocket, logs_url: str, stream_mode: bool = False) -> None:
        if not self._validate_logs_url(logs_url):
            await websocket.send_text("❌ URL des logs invalide.")
            return

        logger.info("Fetching logs", logs_url=logs_url, stream_mode=stream_mode)
        try:
            if stream_mode:
                await self._handle_streaming_logs(websocket, logs_url)
            else:
                await self._handle_static_logs(websocket, logs_url)
        except httpx.TimeoutException:
            await websocket.send_text("⏰ Timeout lors de la récupération des logs.")
        except httpx.HTTPStatusError as exc:
            await websocket.send_text(f"❌ Erreur HTTP {exc.response.status_code} lors de la récupération des logs.")
        except httpx.HTTPError as exc:
            logger.error("Logs transport error", logs_url=logs_url, error=str(exc))
            await websocket.send_text("❌ Erreur réseau lors de la récupération des logs.")

    def _validate_logs_url(self, logs_url: str) -> bool:
        return bool(logs_url and logs_url.startswith(("http://", "https://")))

    async def _handle_streaming_logs(self, websocket: WebSocket, logs_url: str) -> None:
        async with self.http_client.stream("GET", logs_url) as response:
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
        response = await self.http_client.get(logs_url, timeout=30.0)
        logger.debug("Static logs response", status_code=response.status_code)
        response.raise_for_status()

        logs_content = response.text
        if not logs_content.strip():
            await websocket.send_text("📭 Aucun log trouvé pour cette application.")
            return

        log_lines = logs_content.strip().split("\n")
        total_lines = len(log_lines)

        await websocket.send_text(f"📊 {total_lines} lignes de logs récupérées :")
        await websocket.send_text("─" * 50)

        for i in range(0, len(log_lines), settings.log_chunk_size):
            chunk = log_lines[i : i + settings.log_chunk_size]
            await websocket.send_text("\n".join(chunk))
            if i + settings.log_chunk_size < len(log_lines):
                await asyncio.sleep(0.1)

        await websocket.send_text("─" * 50)
        await websocket.send_text(f"✅ Fin des logs ({total_lines} lignes)")
