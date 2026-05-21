"""Application composition root."""
from dataclasses import dataclass

import httpx

from app.config import settings
from app.infrastructure.rasa import RasaClient
from app.infrastructure.scalingo import AppsAPI, ScalingoHTTPClient, build_default_token_provider
from app.services.logs_service import LogsService


@dataclass(frozen=True)
class AppComponents:
    rasa_client: RasaClient
    apps_api: AppsAPI
    logs_service: LogsService


def build_components() -> AppComponents:
    rasa_client = RasaClient(
        base_url=settings.rasa_url,
        timeout_ms=settings.rasa_timeout_ms,
        auth_token=settings.rasa_auth_token,
    )

    token_provider = build_default_token_provider()
    scalingo_http_client = ScalingoHTTPClient(token_provider)
    apps_api = AppsAPI(scalingo_http_client)
    shared_http_client = httpx.AsyncClient(timeout=httpx.Timeout(20.0))

    logs_service = LogsService(apps_api, shared_http_client)
    return AppComponents(
        rasa_client=rasa_client,
        apps_api=apps_api,
        logs_service=logs_service,
    )
