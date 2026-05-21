from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.logging import StructuredLogger

logger = StructuredLogger("rasa_client")


class RasaClient:
    def __init__(self, base_url: str, timeout_ms: int = 3000, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = max(timeout_ms, 1000) / 1000.0
        self.auth_token = auth_token
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def parse_message(self, text: str, retries: int = 1) -> Dict[str, Any]:
        payload = {"text": text}
        params = {"token": self.auth_token} if self.auth_token else None
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                response = await self._client.post(
                    f"{self.base_url}/model/parse",
                    json=payload,
                    params=params,
                    headers={"X-NLU-Contract": settings.nlu_expected_contract},
                )
                response.raise_for_status()
                data = response.json()
                required_keys = {
                    "hypotheses",
                    "final_decision",
                    "entities",
                    "quality_signals",
                    "text_normalized",
                    "model_info",
                }
                if not required_keys.issubset(set(data.keys())):
                    data = self._normalize_legacy_payload(data, text)
                if not required_keys.issubset(set(data.keys())):
                    raise ValueError("Invalid NLU v3 response payload")
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Failed to parse message with Rasa service",
                    attempt=attempt + 1,
                    retries=retries + 1,
                    error=str(exc),
                )
                if attempt < retries:
                    await asyncio.sleep(0.2)

        raise RuntimeError(f"Rasa service unavailable: {last_error}") from last_error

    @staticmethod
    def _normalize_legacy_payload(data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """
        Backward compatibility for older NLU payloads:
        - intent_top1 / intent_ranking / decision
        """
        if "intent_ranking" not in data or "decision" not in data:
            return data

        ranking = data.get("intent_ranking") or []
        hypotheses = []
        for idx, item in enumerate(ranking, start=1):
            hypotheses.append(
                {
                    "name": str(item.get("name", "nlu_fallback")),
                    "confidence": float(item.get("confidence_raw", item.get("confidence_calibrated", 0.0))),
                    "confidence_calibrated": float(item.get("confidence_calibrated", item.get("confidence_raw", 0.0))),
                    "rank": int(item.get("rank", idx)),
                    "rationale_features": {"source": 1.0},
                }
            )

        decision = data.get("decision") or {}
        accepted_intent = str(decision.get("accepted_intent", "nlu_fallback"))
        reason = str(decision.get("reason", "low_confidence"))
        action = "accept" if accepted_intent != "nlu_fallback" and reason == "accepted" else ("clarify" if reason == "low_confidence" else "reject")

        return {
            "hypotheses": hypotheses,
            "final_decision": {
                "action": action,
                "intent": accepted_intent,
                "reason": reason if reason in {"accepted", "low_confidence", "low_margin"} else "accepted",
                "policy": {
                    "min_conf_passed": bool(decision.get("min_conf_passed", False)),
                    "min_margin_passed": bool(decision.get("min_margin_passed", False)),
                },
                "margin": float(decision.get("margin", 0.0)),
            },
            "entities": data.get("entities", []),
            "quality_signals": {
                "ambiguity_score": 1.0 - float(decision.get("margin", 0.0)),
                "ood_likelihood": 0.0,
                "calibration_band": "legacy",
            },
            "text_normalized": str(data.get("text_normalized", original_text)),
            "model_info": {
                "version": str(data.get("model_version", "legacy")),
                "language_profile": str(data.get("language_profile", "legacy")),
            },
        }
