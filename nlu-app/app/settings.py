from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    model_path: str
    rasa_auth_token: str | None
    nlu_contract_version: str
    nlu_model_version: str
    nlu_language_profile: str
    intent_min_confidence: float
    intent_min_margin: float
    intent_topk: int
    entity_min_confidence: float
    nlu_calibration_enabled: bool


def load_settings() -> Settings:
    return Settings(
        model_path=os.getenv("NLU_MODEL_PATH", "models"),
        rasa_auth_token=os.getenv("RASA_AUTH_TOKEN") or os.getenv("NLU_AUTH_TOKEN"),
        nlu_contract_version=os.getenv("NLU_CONTRACT_VERSION", "v3"),
        nlu_model_version=os.getenv("NLU_MODEL_VERSION", "dev"),
        nlu_language_profile=os.getenv("NLU_LANGUAGE_PROFILE", "fr_en_mixed"),
        intent_min_confidence=float(os.getenv("INTENT_MIN_CONFIDENCE", "0.45")),
        intent_min_margin=float(os.getenv("INTENT_MIN_MARGIN", "0.08")),
        intent_topk=int(os.getenv("INTENT_TOPK", "3")),
        entity_min_confidence=float(os.getenv("ENTITY_MIN_CONFIDENCE", "0.0")),
        nlu_calibration_enabled=_as_bool(os.getenv("NLU_CALIBRATION_ENABLED"), default=True),
    )


settings = load_settings()
