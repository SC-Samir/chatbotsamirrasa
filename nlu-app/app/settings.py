from __future__ import annotations

import os


class Settings:
    model_path: str = os.getenv("NLU_MODEL_PATH", "models")
    rasa_auth_token: str | None = os.getenv("RASA_AUTH_TOKEN") or os.getenv("NLU_AUTH_TOKEN")
    nlu_contract_version: str = os.getenv("NLU_CONTRACT_VERSION", "v2")
    nlu_model_version: str = os.getenv("NLU_MODEL_VERSION", "dev")
    nlu_language_profile: str = os.getenv("NLU_LANGUAGE_PROFILE", "fr_en_mixed")
    intent_min_confidence: float = float(os.getenv("INTENT_MIN_CONFIDENCE", "0.6"))
    intent_min_margin: float = float(os.getenv("INTENT_MIN_MARGIN", "0.15"))
    intent_topk: int = int(os.getenv("INTENT_TOPK", "3"))
    entity_min_confidence: float = float(os.getenv("ENTITY_MIN_CONFIDENCE", "0.0"))
    nlu_calibration_enabled: bool = os.getenv("NLU_CALIBRATION_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


settings = Settings()
