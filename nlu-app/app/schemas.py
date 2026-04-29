from __future__ import annotations

from typing import Literal, List

from pydantic import BaseModel


class ParseRequest(BaseModel):
    text: str


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


class ModelInfo(BaseModel):
    version: str
    language_profile: str


class ParseResponseV2(BaseModel):
    intent_top1: IntentScore
    intent_ranking: List[IntentScore]
    decision: Decision
    entities: List[EntityV2]
    text_normalized: str
    model_info: ModelInfo
