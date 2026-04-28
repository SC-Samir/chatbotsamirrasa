"""Application composition root."""
from dataclasses import dataclass

from rasa.core.agent import Agent

from app.application import AddEnvVar, DeleteApp, ListEnvVars, RenameApp, RestartApp, ScaleApp
from app.handlers.intent_handlers import IntentHandlerManager
from app.handlers.websocket_handler import WebSocketHandler
from app.scalingo_manager import ScalingoManager
from app.services.deployment_service import DeploymentService
from app.services.logs_service import LogsService
from app.presentation.websocket import AppManagementIntentController, WebSocketPresenter
from app.config import settings
from app.utils.websocket_helpers import WebSocketHelpers


@dataclass(frozen=True)
class AppComponents:
    agent: Agent
    scalingo_manager: ScalingoManager
    logs_service: LogsService
    deployment_service: DeploymentService
    intent_handler_manager: IntentHandlerManager
    websocket_handler: WebSocketHandler


def build_components() -> AppComponents:
    agent = Agent()
    agent.load_model(settings.rasa_model_path)

    scalingo_manager = ScalingoManager()

    logs_service = LogsService(scalingo_manager)
    deployment_service = DeploymentService(scalingo_manager)
    websocket_helpers = WebSocketHelpers(scalingo_manager)

    gateway = scalingo_manager.apps_api
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
    websocket_handler = WebSocketHandler(agent, intent_handler_manager)

    return AppComponents(
        agent=agent,
        scalingo_manager=scalingo_manager,
        logs_service=logs_service,
        deployment_service=deployment_service,
        intent_handler_manager=intent_handler_manager,
        websocket_handler=websocket_handler,
    )
