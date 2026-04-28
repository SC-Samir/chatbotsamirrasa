from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx

from app.core.logging import StructuredLogger

logger = StructuredLogger("rasa_client")


class RasaClient:
    def __init__(self, base_url: str, timeout_ms: int = 3000, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = max(timeout_ms, 1000) / 1000.0
        self.auth_token = auth_token

    async def parse_message(self, text: str, retries: int = 1) -> Dict[str, Any]:
        payload = {"text": text}
        params = {"token": self.auth_token} if self.auth_token else None
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/model/parse",
                        json=payload,
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()
                    if "intent" not in data or "entities" not in data:
                        raise ValueError("Invalid Rasa response payload")
                    return data
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Failed to parse message with Rasa service",
                    attempt=attempt + 1,
                    retries=retries + 1,
                    error=str(exc),
                )
                if attempt < retries:
                    await asyncio.sleep(0.2)

        raise RuntimeError(f"Rasa service unavailable: {last_error}") from last_error
