from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.nlu import load_model

_MODEL_DIR: str | None = None


def _build_test_model() -> str:
    global _MODEL_DIR
    if _MODEL_DIR is not None:
        return _MODEL_DIR

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "models" / "test-model"

    cmd = [
        "uv",
        "run",
        "python",
        "scripts/train.py",
        "--input",
        "data.nlu.yml",
        "--output",
        str(out_dir),
        "--epochs",
        "1",
        "--base-model",
        "prajjwal1/bert-tiny",
    ]
    subprocess.run(cmd, cwd=root, check=True)

    _MODEL_DIR = str(out_dir)
    return _MODEL_DIR


def _boot_test_app(model_path: str) -> TestClient:
    from app import settings as settings_module
    from app import main as main_module

    settings_module.settings.model_path = model_path
    main_module.on_startup()
    return TestClient(app)


def test_status_endpoint(monkeypatch):
    model_path = _build_test_model()
    monkeypatch.setenv("NLU_MODEL_PATH", model_path)
    client = _boot_test_app(model_path)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_endpoint(monkeypatch):
    model_path = _build_test_model()
    monkeypatch.setenv("NLU_MODEL_PATH", model_path)
    client = _boot_test_app(model_path)
    response = client.post(
        "/model/parse",
<<<<<<< HEAD
        headers={"X-NLU-Contract": "v2"},
=======
        headers={"X-NLU-Contract": "v3"},
>>>>>>> c4c918e (samir)
        json={
            "text": "deploy samirpgvector on osc-fr1 from https://github.com/Scalingo/sample-ruby-rails branch main"
        },
    )
    assert response.status_code == 200
    body = response.json()
<<<<<<< HEAD
    assert "intent_top1" in body
    assert "intent_ranking" in body
    assert "decision" in body
    assert "entities" in body
    assert isinstance(body["intent_top1"]["name"], str)
    assert isinstance(body["intent_top1"]["confidence_calibrated"], float)
=======
    assert "hypotheses" in body
    assert "final_decision" in body
    assert "entities" in body
    assert "quality_signals" in body
    assert isinstance(body["hypotheses"][0]["name"], str)
    assert isinstance(body["hypotheses"][0]["confidence_calibrated"], float)
>>>>>>> c4c918e (samir)


def test_parse_endpoint_rejects_missing_contract_header(monkeypatch):
    model_path = _build_test_model()
    monkeypatch.setenv("NLU_MODEL_PATH", model_path)
    client = _boot_test_app(model_path)
    response = client.post(
        "/model/parse",
        json={"text": "deploy test-app on osc-fr1"},
    )
    assert response.status_code == 400


def test_model_contract_and_entities():
    model_path = _build_test_model()
    model = load_model(model_path)

    parsed = model.parse("rename mon-app to my-new-app")
    assert set(parsed.keys()) == {
<<<<<<< HEAD
        "intent_top1",
        "intent_ranking",
        "decision",
        "entities",
=======
        "hypotheses",
        "final_decision",
        "entities",
        "quality_signals",
>>>>>>> c4c918e (samir)
        "text_normalized",
        "model_info",
    }
    assert isinstance(parsed["entities"], list)
