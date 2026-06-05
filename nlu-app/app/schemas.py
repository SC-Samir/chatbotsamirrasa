from __future__ import annotations

<<<<<<< HEAD
from typing import Literal, List
=======
from typing import Any, List, Literal
>>>>>>> c4c918e (samir)

from pydantic import BaseModel


class ParseRequest(BaseModel):
    text: str


<<<<<<< HEAD
class IntentScore(BaseModel):
    name: str
    confidence_calibrated: float
    confidence_raw: float


class Decision(BaseModel):
    accepted_intent: str
    reason: Literal["low_confidence", "low_margin", "no_entity_support", "accepted"]
    min_conf_passed: bool
    min_margin_passed: bool
    margin: float


class EntityV2(BaseModel):
    entity: str
    value: str
    confidence: float
    normalized_value: str
=======
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
>>>>>>> c4c918e (samir)


class ModelInfo(BaseModel):
    version: str
    language_profile: str


<<<<<<< HEAD
class ParseResponseV2(BaseModel):
    intent_top1: IntentScore
    intent_ranking: List[IntentScore]
    decision: Decision
    entities: List[EntityV2]
=======
class QualitySignals(BaseModel):
    ambiguity_score: float
    ood_likelihood: float
    calibration_band: Literal["high", "medium", "low"]


class ParseResponseV3(BaseModel):
    hypotheses: List[IntentHypothesis]
    final_decision: FinalDecision
    entities: List[EntityV3]
    quality_signals: QualitySignals
>>>>>>> c4c918e (samir)
    text_normalized: str
    model_info: ModelInfo
