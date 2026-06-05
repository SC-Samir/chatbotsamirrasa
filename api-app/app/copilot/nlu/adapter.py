"""
NLU adapter for intent recognition and entity extraction.

This module adapts the Rasa NLU client responses to the internal
command processing format expected by the orchestration engine.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.infrastructure.rasa.client import RasaClient
from app.copilot.contracts import (
    Decision,
    EntitySet,
    IntentCandidate,
    MemoryHints,
    NLUInterpretation,
    QualitySignals,
)


class NLUAdapter:
    def __init__(self, rasa_client: RasaClient):
        self.rasa_client = rasa_client

    async def interpret(self, text: str) -> NLUInterpretation:
        payload = await self.rasa_client.parse_message(text=text, retries=1)

        candidates: List[IntentCandidate] = []
        for rank, item in enumerate(payload.get("hypotheses", []), start=1):
            candidates.append(
                IntentCandidate(
                    name=str(item.get("name", "nlu_fallback")),
                    confidence=float(item.get("confidence", 0.0)),
                    confidence_calibrated=float(item.get("confidence_calibrated", item.get("confidence", 0.0))),
                    rank=int(item.get("rank", rank)),
                )
            )

        decision_raw: Dict[str, Any] = payload.get("final_decision", {})
        decision = Decision(
            action=str(decision_raw.get("action", "reject")),  # type: ignore[arg-type]
            intent=str(decision_raw.get("intent", "nlu_fallback")),
            reason=str(decision_raw.get("reason", "unknown")),
            margin=float(decision_raw.get("margin", 0.0)),
            policy=dict(decision_raw.get("policy", {})),
        )

        entities = {
            str(item.get("entity", "")): item.get("normalized_value", item.get("value"))
            for item in payload.get("entities", [])
            if item.get("entity")
        }

        quality_raw = payload.get("quality_signals", {})
        quality = QualitySignals(
            ambiguity_score=float(quality_raw.get("ambiguity_score", 1.0)),
            ood_likelihood=float(quality_raw.get("ood_likelihood", 1.0)),
            calibration_band=str(quality_raw.get("calibration_band", "low")),
        )

        should_persist = decision.action == "accept" and quality.ood_likelihood < 0.6
        memory_hints = MemoryHints(
            should_persist=should_persist,
            confidence=float(candidates[0].confidence_calibrated) if candidates else 0.0,
            touched_keys=sorted(list(entities.keys())),
        )

        return NLUInterpretation(
            candidates=candidates,
            decision=decision,
            entities=EntitySet(values=entities),
            quality=quality,
            memory_hints=memory_hints,
            normalized_text=str(payload.get("text_normalized", text)),
            model_info=dict(payload.get("model_info", {})),
        )
