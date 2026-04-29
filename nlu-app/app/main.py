from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from app.nlu import NLUModel, load_model
from app.schemas import ParseRequest, ParseResponseV2
from app.settings import settings

_nlu_model: Optional[NLUModel] = None


def ensure_token(token: str | None = Query(default=None)) -> None:
    configured_token = settings.rasa_auth_token
    if not configured_token:
        return
    if token != configured_token:
        raise HTTPException(status_code=401, detail="Invalid auth token")


def ensure_contract(contract: str | None = Header(default=None, alias="X-NLU-Contract")) -> None:
    if contract != settings.nlu_contract_version:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid NLU contract version. Expected {settings.nlu_contract_version}.",
        )


def get_model() -> NLUModel:
    if _nlu_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return _nlu_model


@asynccontextmanager
async def lifespan(_: FastAPI):
    on_startup()
    yield


def on_startup() -> None:
    global _nlu_model
    try:
        _nlu_model = load_model(settings.model_path)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Failed to load NLU model artifacts: {exc}") from exc


app = FastAPI(title="chatbotsamir-nlu", version="0.1.0", lifespan=lifespan)


@app.get("/status")
def status() -> dict:
    return {"status": "ok", "model_path": settings.model_path}


@app.post("/model/parse", response_model=ParseResponseV2)
def parse(
    payload: ParseRequest,
    _: None = Depends(ensure_token),
    __: None = Depends(ensure_contract),
    model: NLUModel = Depends(get_model),
) -> dict:
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Text is required")
    return model.parse(payload.text)
