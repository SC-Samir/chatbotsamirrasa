from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

RiskLevel = Literal["none", "low", "high"]
DecisionAction = Literal["accept", "clarify", "reject"]


@dataclass(frozen=True)
class IntentCandidate:
    name: str
    confidence: float
    confidence_calibrated: float
    rank: int


@dataclass(frozen=True)
class Decision:
    action: DecisionAction
    intent: str
    reason: str
    margin: float
    policy: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntitySet:
    values: Dict[str, Any]


@dataclass(frozen=True)
class QualitySignals:
    ambiguity_score: float
    ood_likelihood: float
    calibration_band: str


@dataclass(frozen=True)
class MemoryHints:
    should_persist: bool
    confidence: float
    touched_keys: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class NLUInterpretation:
    candidates: List[IntentCandidate]
    decision: Decision
    entities: EntitySet
    quality: QualitySignals
    memory_hints: MemoryHints
    normalized_text: str
    model_info: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandContext:
    session_id: str
    user_id: str
    app_scope: Optional[str]
    region_scope: Optional[str]
    trace_id: str


@dataclass(frozen=True)
class CommandRequest:
    command: str
    entities: Dict[str, Any]
    raw_text: str
    context: CommandContext


@dataclass(frozen=True)
class CommandResult:
    event_type: str
    status: Literal["success", "warning", "error", "requires_confirmation"]
    human_message: str
    structured_payload: Dict[str, Any] = field(default_factory=dict)
    next_actions: List[str] = field(default_factory=list)
    risk_level: RiskLevel = "none"
    action_id: Optional[str] = None
