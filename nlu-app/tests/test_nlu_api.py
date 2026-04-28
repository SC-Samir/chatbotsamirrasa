from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.nlu import convert_rasa_nlu, save_model, train_model


def _build_test_model() -> str:
    data_file = Path(__file__).resolve().parents[1] / "data.nlu.yml"
    samples, known_values = convert_rasa_nlu(str(data_file))
    model = train_model(samples=samples, known_values=known_values)
    out = Path(__file__).resolve().parents[1] / "models" / "test-model.joblib"
    save_model(model, str(out))
    return str(out)


def test_status_endpoint(monkeypatch):
    model_path = _build_test_model()
    monkeypatch.setenv("NLU_MODEL_PATH", model_path)

    from app import settings as settings_module
    from app import main as main_module

    settings_module.settings.model_path = model_path
    main_module.on_startup()

    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_endpoint(monkeypatch):
    model_path = _build_test_model()
    monkeypatch.setenv("NLU_MODEL_PATH", model_path)

    from app import settings as settings_module
    from app import main as main_module

    settings_module.settings.model_path = model_path
    main_module.on_startup()

    client = TestClient(app)
    response = client.post(
        "/model/parse",
        json={
            "text": "deploy samirpgvector on osc-fr1 from https://github.com/Scalingo/sample-ruby-rails branch main"
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "intent" in body
    assert "entities" in body
    assert body["intent"]["name"] in {
        "deploy",
        "create_and_deploy",
    }
    assert any(entity["entity"] == "region" for entity in body["entities"])
