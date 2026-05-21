from app.core.composition import build_components


def test_build_components_returns_core_services():
    components = build_components()
    assert components.apps_api is not None
    assert components.logs_service is not None
