import json

import pytest

from app.domain import OperationResult
from app.models import AppContext, IntentResponse
from app.presentation.websocket.app_management_intent_controller import AppManagementIntentController


class FakeUseCase:
    def __init__(self, result):
        self.result = result
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        return self.result


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_text(self, message: str):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_controller_routes_restart_and_emits_structured_messages():
    restart = FakeUseCase(OperationResult.ok(type("X", (), {"accepted": True})()))
    noop = FakeUseCase(OperationResult.ok(None))

    controller = AppManagementIntentController(
        restart_app=restart,
        scale_app=noop,
        delete_app=noop,
        rename_app=noop,
        list_env_vars=noop,
        add_env_var=noop,
    )

    websocket = FakeWebSocket()
    context = AppContext()
    intent = IntentResponse(
        intent_top1={"name": "restart", "confidence_calibrated": 0.98, "confidence_raw": 0.95},
        intent_ranking=[{"name": "restart", "confidence_calibrated": 0.98, "confidence_raw": 0.95}],
        decision={
            "accepted_intent": "restart",
            "reason": "accepted",
            "min_conf_passed": True,
            "min_margin_passed": True,
            "margin": 0.7,
        },
        entities=[
            {"entity": "app_name", "value": "demo-app"},
            {"entity": "region", "value": "osc-fr1"},
        ],
        text_normalized="restart demo-app",
        model_info={"version": "test", "language_profile": "fr_en_mixed"},
    )

    handled = await controller.handle(websocket, intent, context)

    assert handled is True
    assert len(restart.commands) == 1

    progress = json.loads(websocket.messages[0])
    success = json.loads(websocket.messages[1])
    assert progress["kind"] == "progress"
    assert success["kind"] == "success"


@pytest.mark.asyncio
async def test_controller_returns_validation_message_on_missing_params():
    noop = FakeUseCase(OperationResult.ok(None))

    controller = AppManagementIntentController(
        restart_app=noop,
        scale_app=noop,
        delete_app=noop,
        rename_app=noop,
        list_env_vars=noop,
        add_env_var=noop,
    )

    websocket = FakeWebSocket()
    context = AppContext()
    intent = IntentResponse(
        intent_top1={"name": "delete_app", "confidence_calibrated": 0.7, "confidence_raw": 0.7},
        intent_ranking=[{"name": "delete_app", "confidence_calibrated": 0.7, "confidence_raw": 0.7}],
        decision={
            "accepted_intent": "delete_app",
            "reason": "accepted",
            "min_conf_passed": True,
            "min_margin_passed": True,
            "margin": 0.6,
        },
        entities=[],
        text_normalized="delete",
        model_info={"version": "test", "language_profile": "fr_en_mixed"},
    )

    handled = await controller.handle(websocket, intent, context)

    assert handled is True
    payload = json.loads(websocket.messages[-1])
    assert payload["kind"] == "error"
    assert "Missing required params" in payload["message"]
