"""Bearer token exchange and refresh for Scalingo auth."""
import time
from typing import Optional

import httpx

from app.config import settings
from app.core.logging import StructuredLogger

logger = StructuredLogger("scalingo_auth")


class AuthTokenProvider:
    def __init__(self, api_token: str, auth_url: str = "https://auth.scalingo.com/v1/tokens/exchange"):
        if not api_token:
            raise ValueError("SCALINGO_API_TOKEN is required")
        self._api_token = api_token
        self._auth_url = auth_url
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        if self._token is None or time.time() >= self._expires_at:
            self.refresh()
        return self._token  # type: ignore[return-value]

    def refresh(self) -> str:
        timeout = httpx.Timeout(10.0)
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(self._auth_url, auth=("", self._api_token))
                    response.raise_for_status()
                    payload = response.json()
                break
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                last_error = exc
                logger.warning(
                    "Bearer token exchange failed",
                    attempt=attempt,
                    max_attempts=3,
                    error=str(exc),
                )
                if attempt < 3:
                    time.sleep(0.6 * attempt)
                continue
        else:
            raise RuntimeError(f"Unable to exchange Scalingo token: {last_error}")

        token = payload.get("token")
        if not token:
            raise ValueError("Scalingo auth response did not return a bearer token")

        expires_in = int(payload.get("expires_in", 3600))
        self._token = token
        self._expires_at = time.time() + max(expires_in - 30, 30)

        logger.debug("Bearer token refreshed", expires_in=expires_in)
        return token


def build_default_token_provider() -> AuthTokenProvider:
    return AuthTokenProvider(api_token=settings.scalingo_api_token)
