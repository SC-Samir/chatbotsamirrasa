from app.core.composition import build_components


def test_build_components_disables_legacy_stack_when_flag_false():
    components = build_components(enable_legacy_intent_stack=False)
    assert components.intent_handler_manager is None
    assert components.websocket_handler is None


def test_build_components_enables_legacy_stack_when_flag_true():
    components = build_components(enable_legacy_intent_stack=True)
    assert components.intent_handler_manager is not None
    assert components.websocket_handler is not None
