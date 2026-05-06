from __future__ import annotations

from typing import Any, List, Literal

from pydantic import BaseModel


class ParseRequest(BaseModel):
    text: str


class IntentHypothesis(BaseModel):
    name: str
    confidence: float
    confidence_calibrated: float
    rank: int
    rationale_features: dict[str, float]


class FinalDecision(BaseModel):
    action: Literal["accept", "clarify", "reject"]
    intent: str
    reason: Literal["low_confidence", "low_margin", "accepted"]
    policy: dict[str, Any]
    margin: float


class EntityV3(BaseModel):
    entity: str
    value: str
    start: int
    end: int
    confidence: float
    normalized_value: str
    provenance: Literal["ml", "rule"]


class ModelInfo(BaseModel):
    version: str
    language_profile: str


class QualitySignals(BaseModel):
    ambiguity_score: float
    ood_likelihood: float
    calibration_band: Literal["high", "medium", "low"]


class ParseResponseV3(BaseModel):
    hypotheses: List[IntentHypothesis]
    final_decision: FinalDecision
    entities: List[EntityV3]
    quality_signals: QualitySignals
    text_normalized: str
    model_info: ModelInfo
