from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from app.nlu import NLUModel, load_model
from app.schemas import ParseRequest, ParseResponse
from app.settings import settings

app = FastAPI(title="chatbotsamir-nlu", version="0.1.0")
_nlu_model: Optional[NLUModel] = None


def ensure_token(token: str | None = Query(default=None)) -> None:
    configured_token = settings.rasa_auth_token
    if not configured_token:
        return
    if token != configured_token:
        raise HTTPException(status_code=401, detail="Invalid auth token")


@app.on_event("startup")
def on_startup() -> None:
    global _nlu_model
    try:
        _nlu_model = load_model(settings.model_path)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Failed to load NLU model artifacts: {exc}") from exc


@app.get("/status")
def status() -> dict:
    return {"status": "ok", "model_path": settings.model_path}


@app.post("/model/parse", response_model=ParseResponse)
def parse(payload: ParseRequest, _: None = Depends(ensure_token)) -> dict:
    if _nlu_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Text is required")
    return _nlu_model.parse(payload.text)
