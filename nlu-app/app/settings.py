from __future__ import annotations

import os


class Settings:
    model_path: str = os.getenv("NLU_MODEL_PATH", "models")
    rasa_auth_token: str | None = os.getenv("RASA_AUTH_TOKEN") or os.getenv("NLU_AUTH_TOKEN")


settings = Settings()
