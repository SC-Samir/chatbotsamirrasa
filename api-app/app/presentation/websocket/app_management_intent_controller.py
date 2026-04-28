"""Thin app-management intent controller."""
from typing import Any, Dict, Optional

from fastapi import WebSocket

from app.application import (
    AddEnvVar,
    AddEnvVarCommand,
    DeleteApp,
    DeleteAppCommand,
    ListEnvVars,
    ListEnvVarsCommand,
    RenameApp,
    RenameAppCommand,
    RestartApp,
    RestartAppCommand,
    ScaleApp,
    ScaleAppCommand,
)
from app.domain import FailureReason, OperationError
from app.models import AppContext, IntentResponse
from app.presentation.websocket.messages import WebSocketPresenter
from app.utils.context_manager import ContextManager


class AppManagementIntentController:
    SUPPORTED_INTENTS = {
        "restart",
        "scale",
        "delete_app",
        "rename_app",
        "list_env_vars",
        "add_env_var",
    }

    def __init__(
        self,
        restart_app: RestartApp,
        scale_app: ScaleApp,
        delete_app: DeleteApp,
        rename_app: RenameApp,
        list_env_vars: ListEnvVars,
        add_env_var: AddEnvVar,
        presenter: Optional[WebSocketPresenter] = None,
    ):
        self.restart_app = restart_app
        self.scale_app = scale_app
        self.delete_app = delete_app
        self.rename_app = rename_app
        self.list_env_vars = list_env_vars
        self.add_env_var = add_env_var
        self.presenter = presenter or WebSocketPresenter()
        self.context_manager = ContextManager()

    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        intent_name = intent_response.intent.get("name")
        if intent_name not in self.SUPPORTED_INTENTS:
            return False

        entities = self.context_manager.extract_entities(intent_response)
        self.context_manager.update_context_from_entities(entities, context)

        if intent_name == "restart":
            await self._handle_restart(websocket, entities, context)
            return True
        if intent_name == "scale":
            await self._handle_scale(websocket, entities, context)
            return True
        if intent_name == "delete_app":
            await self._handle_delete(websocket, entities, context)
            return True
        if intent_name == "rename_app":
            await self._handle_rename(websocket, entities, context)
            return True
        if intent_name == "list_env_vars":
            await self._handle_list_env_vars(websocket, entities, context)
            return True
        if intent_name == "add_env_var":
            await self._handle_add_env_var(websocket, entities, context)
            return True

        return False

    async def _handle_restart(self, websocket: WebSocket, entities: Dict[str, Any], context: AppContext) -> None:
        params = self._required_params(entities, context, ["app_name", "region"])
        if not params:
            await self.presenter.error(websocket, "Missing required params: app_name and region")
            return

        command = RestartAppCommand(
            app_name=params["app_name"],
            region=params["region"],
            scope=entities.get("scope"),
        )
        await self.presenter.progress(websocket, "Submitting restart request")
        result = self.restart_app.execute(command)

        if not result.success:
            await self._present_error(websocket, result.error)
            return

        await self.presenter.success(
            websocket,
            f"Restart accepted for {params['app_name']} in {params['region']}",
            data={"app_name": params["app_name"], "region": params["region"]},
        )

    async def _handle_scale(self, websocket: WebSocket, entities: Dict[str, Any], context: AppContext) -> None:
        params = self._required_params(entities, context, ["app_name", "region", "container_name", "container_amount"])
        if not params:
            await self.presenter.error(
                websocket,
                "Missing required params: app_name, region, container_name and container_amount",
            )
            return

        command = ScaleAppCommand(
            app_name=params["app_name"],
            region=params["region"],
            container_name=params["container_name"],
            container_amount=str(params["container_amount"]),
            container_size=entities.get("container_size"),
        )
        await self.presenter.progress(websocket, "Submitting scale request")
        result = self.scale_app.execute(command)

        if not result.success:
            await self._present_error(websocket, result.error)
            return

        await self.presenter.success(
            websocket,
            f"Scale accepted for {params['app_name']} in {params['region']}",
            data={"containers": result.value.containers},
        )

    async def _handle_delete(self, websocket: WebSocket, entities: Dict[str, Any], context: AppContext) -> None:
        params = self._required_params(entities, context, ["app_name", "region"])
        if not params:
            await self.presenter.error(websocket, "Missing required params: app_name and region")
            return

        command = DeleteAppCommand(app_name=params["app_name"], region=params["region"])
        await self.presenter.progress(websocket, "Submitting delete request")
        result = self.delete_app.execute(command)

        if not result.success:
            await self._present_error(websocket, result.error)
            return

        if context.app_name == params["app_name"]:
            context.app_name = None

        await self.presenter.success(
            websocket,
            f"Application {params['app_name']} deleted",
            data={"app_name": params["app_name"], "region": params["region"]},
        )

    async def _handle_rename(self, websocket: WebSocket, entities: Dict[str, Any], context: AppContext) -> None:
        params = self._required_params(entities, context, ["app_name", "region", "new_name"])
        if not params:
            await self.presenter.error(websocket, "Missing required params: app_name, region and new_name")
            return

        command = RenameAppCommand(
            app_name=params["app_name"],
            region=params["region"],
            new_name=params["new_name"],
        )
        await self.presenter.progress(websocket, "Submitting rename request")
        result = self.rename_app.execute(command)

        if not result.success:
            await self._present_error(websocket, result.error)
            return

        if context.app_name == params["app_name"]:
            context.app_name = params["new_name"]

        await self.presenter.success(
            websocket,
            f"Application renamed from {params['app_name']} to {params['new_name']}",
            data={"app": result.value.app},
        )

    async def _handle_list_env_vars(self, websocket: WebSocket, entities: Dict[str, Any], context: AppContext) -> None:
        params = self._required_params(entities, context, ["app_name", "region"])
        if not params:
            await self.presenter.error(websocket, "Missing required params: app_name and region")
            return

        aliases_raw = entities.get("aliases", "true")
        aliases = str(aliases_raw).lower() == "true"

        command = ListEnvVarsCommand(app_name=params["app_name"], region=params["region"], aliases=aliases)
        await self.presenter.progress(websocket, "Fetching environment variables")
        result = self.list_env_vars.execute(command)

        if not result.success:
            await self._present_error(websocket, result.error)
            return

        variables = [
            {
                "name": item.name,
                "value": self._mask_sensitive_value(item.name, item.value),
                "id": item.var_id,
            }
            for item in result.value.variables
        ]
        await self.presenter.success(
            websocket,
            f"Found {len(variables)} environment variables",
            data={"variables": variables, "aliases": aliases},
        )

    async def _handle_add_env_var(self, websocket: WebSocket, entities: Dict[str, Any], context: AppContext) -> None:
        params = self._required_params(
            entities,
            context,
            ["app_name", "region", "variable_name", "variable_value"],
        )
        if not params:
            await self.presenter.error(
                websocket,
                "Missing required params: app_name, region, variable_name and variable_value",
            )
            return

        command = AddEnvVarCommand(
            app_name=params["app_name"],
            region=params["region"],
            variable_name=params["variable_name"],
            variable_value=params["variable_value"],
        )
        await self.presenter.progress(websocket, "Adding environment variable")
        result = self.add_env_var.execute(command)

        if not result.success:
            await self._present_error(websocket, result.error)
            return

        await self.presenter.success(
            websocket,
            f"Environment variable {params['variable_name']} added",
            data={
                "name": result.value.variable.name,
                "value": self._mask_sensitive_value(result.value.variable.name, result.value.variable.value),
                "id": result.value.variable.var_id,
            },
        )

    async def _present_error(self, websocket: WebSocket, error: Optional[OperationError]) -> None:
        if error is None:
            await self.presenter.error(websocket, "Unknown operation failure")
            return

        if error.reason in (FailureReason.VALIDATION, FailureReason.CONFLICT):
            await self.presenter.warning(websocket, error.message, data=error.details)
            return

        await self.presenter.error(websocket, error.message, data=error.details)

    def _required_params(
        self,
        entities: Dict[str, Any],
        context: AppContext,
        required_fields: list,
    ) -> Optional[Dict[str, Any]]:
        params = self.context_manager.get_required_params(entities, context, required_fields)
        missing = [field for field in required_fields if not params.get(field)]
        if missing:
            return None
        return params

    def _mask_sensitive_value(self, name: str, value: str) -> str:
        sensitive_patterns = (
            "password",
            "passwd",
            "pwd",
            "secret",
            "key",
            "token",
            "auth",
            "credential",
            "private",
            "api_key",
            "access_key",
            "secret_key",
        )
        lower_name = name.lower()
        if any(pattern in lower_name for pattern in sensitive_patterns):
            if len(value) <= 4:
                return "*" * len(value)
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
        return value
