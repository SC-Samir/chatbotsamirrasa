"""Application composition root."""
from dataclasses import dataclass

import httpx

from app.application import AddEnvVar, DeleteApp, ListEnvVars, RenameApp, RestartApp, ScaleApp
from app.handlers.intent_handlers import IntentHandlerManager
from app.handlers.websocket_handler import WebSocketHandler
from app.services.deployment_service import DeploymentService
from app.services.logs_service import LogsService
from app.presentation.websocket import AppManagementIntentController, WebSocketPresenter
from app.config import settings
from app.infrastructure.rasa import RasaClient
from app.infrastructure.scalingo import AppsAPI, ScalingoHTTPClient, build_default_token_provider
from app.utils.websocket_helpers import WebSocketHelpers


@dataclass(frozen=True)
class AppComponents:
    rasa_client: RasaClient
    apps_api: AppsAPI
    logs_service: LogsService
    deployment_service: DeploymentService
    intent_handler_manager: IntentHandlerManager
    websocket_handler: WebSocketHandler


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
    deployment_service = DeploymentService(apps_api)
    websocket_helpers = WebSocketHelpers(apps_api)

    gateway = apps_api
    app_management_controller = AppManagementIntentController(
        restart_app=RestartApp(gateway),
        scale_app=ScaleApp(gateway),
        delete_app=DeleteApp(gateway),
        rename_app=RenameApp(gateway),
        list_env_vars=ListEnvVars(gateway),
        add_env_var=AddEnvVar(gateway),
        presenter=WebSocketPresenter(),
    )

    intent_handler_manager = IntentHandlerManager(
        deployment_service=deployment_service,
        logs_service=logs_service,
        websocket_helpers=websocket_helpers,
        app_management_controller=app_management_controller,
    )
    websocket_handler = WebSocketHandler(rasa_client, intent_handler_manager)

    return AppComponents(
        rasa_client=rasa_client,
        apps_api=apps_api,
        logs_service=logs_service,
        deployment_service=deployment_service,
        intent_handler_manager=intent_handler_manager,
        websocket_handler=websocket_handler,
    )
