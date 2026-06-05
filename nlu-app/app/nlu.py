from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from transformers import pipeline

from app.settings import settings

ANNOTATED_RE = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")
INTENT_FALLBACK = "nlu_fallback"
APP_NAME_HINT_RE = re.compile(
    r"\b(?:of|for|app|application)\s+([a-z0-9][a-z0-9-]{1,62})\b",
    re.IGNORECASE,
)
REGION_HINT_RE = re.compile(r"\b(osc(?:\s*-\s*|-)fr1|osc(?:\s*-\s*|-)secnum(?:\s*-\s*|-)fr1)\b", re.IGNORECASE)
NEW_NAME_HINT_RE = re.compile(r"\b(?:rename|change)\b.*?\bto\s+([a-z0-9][a-z0-9-]{1,62})\b", re.IGNORECASE)
VAR_ASSIGN_RE = re.compile(
    r"\b(?:add|set|create)\s+([A-Z][A-Z0-9_]{1,63})\s*=\s*(.+?)(?:\s+\b(?:to|for)\b\s+[a-z0-9][a-z0-9-]{1,62}(?:\s+\bon\b\s+osc(?:\s*-\s*|-)(?:fr1|secnum(?:\s*-\s*|-)fr1))?)?$",
    re.IGNORECASE,
)


class NLUModel:
    def __init__(
        self,
        intent_pipe: Any,
        ner_pipe: Any,
        id2intent: Dict[str, str],
        allowed_entities: List[str],
        model_version: str,
        language_profile: str,
        temperature: float,
    ):
        self.intent_pipe = intent_pipe
        self.ner_pipe = ner_pipe
        self.id2intent = id2intent
        self.allowed_entities = set(allowed_entities)
        self.model_version = model_version
        self.language_profile = language_profile
        self.temperature = max(temperature, 1e-6)

    def parse(self, text: str) -> Dict[str, Any]:
        normalized = text.strip()
        ranking = self._predict_intents(normalized)
        top1 = ranking[0] if ranking else {"name": INTENT_FALLBACK, "confidence": 0.0, "confidence_calibrated": 0.0}
        top2 = ranking[1] if len(ranking) > 1 else {"confidence_calibrated": 0.0}
        decision = self._build_decision(top1, top2)

        entities = self._extract_entities(normalized)
        entities = self._apply_rule_based_entity_overrides(normalized, entities)
        hypotheses = ranking[: max(1, settings.intent_topk)]
        quality_signals = self._build_quality_signals(hypotheses, decision)
        return {
            "hypotheses": hypotheses,
            "final_decision": decision,
            "entities": entities,
            "quality_signals": quality_signals,
            "text_normalized": normalized,
            "model_info": {
                "version": self.model_version,
                "language_profile": self.language_profile,
            },
        }

    def _apply_rule_based_entity_overrides(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Patch critical entities from raw text when token classification returns broken wordpieces."""
        app_name = self._extract_app_name_from_text(text)
        region = self._extract_region_from_text(text)
        new_name = self._extract_new_name_from_text(text)
        variable_name, variable_value = self._extract_variable_assignment_from_text(text)
        if not app_name:
            app_name = None

        updated = []
        replaced_app = False
        replaced_region = False
        replaced_new_name = False
        replaced_var_name = False
        replaced_var_value = False
        for ent in entities:
            if ent.get("entity") == "app_name":
                if not app_name:
                    continue
                updated.append(
                    {
                        "entity": "app_name",
                        "value": app_name,
                        "start": int(text.lower().find(app_name.lower())),
                        "end": int(text.lower().find(app_name.lower()) + len(app_name)),
                        "confidence": max(float(ent.get("confidence", 0.0)), 0.99),
                        "normalized_value": app_name.lower(),
                        "provenance": "rule",
                    }
                )
                replaced_app = True
            elif ent.get("entity") == "region" and region:
                updated.append(
                    {
                        "entity": "region",
                        "value": region,
                        "start": int(text.lower().find(region.lower())),
                        "end": int(text.lower().find(region.lower()) + len(region)),
                        "confidence": max(float(ent.get("confidence", 0.0)), 0.99),
                        "normalized_value": region.lower(),
                        "provenance": "rule",
                    }
                )
                replaced_region = True
            elif ent.get("entity") == "new_name" and new_name:
                updated.append(
                    {
                        "entity": "new_name",
                        "value": new_name,
                        "start": int(text.lower().find(new_name.lower())),
                        "end": int(text.lower().find(new_name.lower()) + len(new_name)),
                        "confidence": max(float(ent.get("confidence", 0.0)), 0.99),
                        "normalized_value": new_name.lower(),
                        "provenance": "rule",
                    }
                )
                replaced_new_name = True
            elif ent.get("entity") == "variable_name" and variable_name:
                updated.append(
                    {
                        "entity": "variable_name",
                        "value": variable_name,
                        "start": int(text.find(variable_name)),
                        "end": int(text.find(variable_name) + len(variable_name)),
                        "confidence": max(float(ent.get("confidence", 0.0)), 0.99),
                        "normalized_value": variable_name,
                        "provenance": "rule",
                    }
                )
                replaced_var_name = True
            elif ent.get("entity") == "variable_value" and variable_value:
                updated.append(
                    {
                        "entity": "variable_value",
                        "value": variable_value,
                        "start": int(text.lower().find(variable_value.lower())),
                        "end": int(text.lower().find(variable_value.lower()) + len(variable_value)),
                        "confidence": max(float(ent.get("confidence", 0.0)), 0.99),
                        "normalized_value": variable_value,
                        "provenance": "rule",
                    }
                )
                replaced_var_value = True
            else:
                updated.append(ent)

        if app_name and not replaced_app:
            start = int(text.lower().find(app_name.lower()))
            updated.append(
                {
                    "entity": "app_name",
                    "value": app_name,
                    "start": start,
                    "end": start + len(app_name),
                    "confidence": 0.99,
                    "normalized_value": app_name.lower(),
                    "provenance": "rule",
                }
            )
        if region and not replaced_region:
            start = int(text.lower().find(region.lower()))
            updated.append(
                {
                    "entity": "region",
                    "value": region,
                    "start": start,
                    "end": start + len(region),
                    "confidence": 0.99,
                    "normalized_value": region.lower(),
                    "provenance": "rule",
                }
            )
        if new_name and not replaced_new_name:
            start = int(text.lower().find(new_name.lower()))
            updated.append(
                {
                    "entity": "new_name",
                    "value": new_name,
                    "start": start,
                    "end": start + len(new_name),
                    "confidence": 0.99,
                    "normalized_value": new_name.lower(),
                    "provenance": "rule",
                }
            )
        if variable_name and not replaced_var_name:
            start = int(text.find(variable_name))
            updated.append(
                {
                    "entity": "variable_name",
                    "value": variable_name,
                    "start": start,
                    "end": start + len(variable_name),
                    "confidence": 0.99,
                    "normalized_value": variable_name,
                    "provenance": "rule",
                }
            )
        if variable_value and not replaced_var_value:
            start = int(text.lower().find(variable_value.lower()))
            updated.append(
                {
                    "entity": "variable_value",
                    "value": variable_value,
                    "start": start,
                    "end": start + len(variable_value),
                    "confidence": 0.99,
                    "normalized_value": variable_value,
                    "provenance": "rule",
                }
            )
        return self._dedupe_entities(updated)

    @staticmethod
    def _extract_app_name_from_text(text: str) -> str | None:
        match = APP_NAME_HINT_RE.search(text)
        if not match:
            return None
        candidate = match.group(1).strip().lower()
        if candidate in {"osc-fr1", "osc-secnum-fr1"}:
            return None
        return candidate

    @staticmethod
    def _extract_region_from_text(text: str) -> str | None:
        match = REGION_HINT_RE.search(text)
        if not match:
            return None
        return re.sub(r"\s+", "", match.group(1).lower())

    @staticmethod
    def _extract_new_name_from_text(text: str) -> str | None:
        match = NEW_NAME_HINT_RE.search(text)
        if not match:
            return None
        return match.group(1).strip().lower()

    @staticmethod
    def _extract_variable_assignment_from_text(text: str) -> tuple[str | None, str | None]:
        match = VAR_ASSIGN_RE.search(text.strip())
        if not match:
            return None, None
        var_name = match.group(1).strip().upper()
        var_value = match.group(2).strip()
        return var_name, var_value

    @staticmethod
    def _dedupe_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for ent in entities:
            key = (str(ent.get("entity", "")), str(ent.get("normalized_value", ent.get("value", ""))).lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ent)
        return deduped

    @staticmethod
    def _build_decision(top1: Dict[str, Any], top2: Dict[str, Any]) -> Dict[str, Any]:
        margin = float(top1["confidence_calibrated"] - top2["confidence_calibrated"])
        min_conf_passed = float(top1["confidence_calibrated"]) >= settings.intent_min_confidence
        min_margin_passed = margin >= settings.intent_min_margin

        action = "accept"
        intent = str(top1["name"])
        reason = "accepted"
        if not min_conf_passed:
            action = "reject"
            intent = INTENT_FALLBACK
            reason = "low_confidence"
        elif not min_margin_passed:
            action = "clarify"
            intent = INTENT_FALLBACK
            reason = "low_margin"

        return {
            "action": action,
            "intent": intent,
            "reason": reason,
            "policy": {
                "min_confidence_threshold": settings.intent_min_confidence,
                "min_margin_threshold": settings.intent_min_margin,
                "min_conf_passed": bool(min_conf_passed),
                "min_margin_passed": bool(min_margin_passed),
            },
            "margin": margin,
        }

    @staticmethod
    def _build_quality_signals(hypotheses: List[Dict[str, Any]], decision: Dict[str, Any]) -> Dict[str, Any]:
        top1 = hypotheses[0] if hypotheses else {"confidence_calibrated": 0.0}
        confidence = float(top1.get("confidence_calibrated", 0.0))
        ambiguity = 1.0 - min(max(float(decision.get("margin", 0.0)), 0.0), 1.0)
        ood_likelihood = 1.0 - confidence
        if confidence >= 0.85:
            band = "high"
        elif confidence >= 0.6:
            band = "medium"
        else:
            band = "low"
        return {
            "ambiguity_score": ambiguity,
            "ood_likelihood": ood_likelihood,
            "calibration_band": band,
        }

    def _calibrate_score(self, score: float) -> float:
        if not settings.nlu_calibration_enabled:
            return float(score)
        # Temperature scaling approximation over model confidence.
        score = min(max(float(score), 1e-6), 1.0 - 1e-6)
        logit = math.log(score / (1.0 - score))
        calibrated = 1.0 / (1.0 + math.exp(-(logit / self.temperature)))
        return float(calibrated)

    def _predict_intents(self, text: str) -> List[Dict[str, Any]]:
        results = self.intent_pipe(text, truncation=True, max_length=128, top_k=None)
        ranking: List[Dict[str, Any]] = []
        for result in results:
            label = str(result.get("label", ""))
            intent_name = self._resolve_intent_label(label)
            raw_score = float(result.get("score", 0.0))
            ranking.append(
                {
                    "name": intent_name,
                    "confidence": raw_score,
                    "confidence_calibrated": self._calibrate_score(raw_score),
                    "rank": 0,
                    "rationale_features": {
                        "raw_confidence": raw_score,
                    },
                },
            )
        ranking.sort(key=lambda item: float(item["confidence_calibrated"]), reverse=True)
        for idx, item in enumerate(ranking, start=1):
            item["rank"] = idx
        return ranking

    def _resolve_intent_label(self, label: str) -> str:
        if label in self.id2intent:
            return str(self.id2intent[label])
        match = re.match(r"^LABEL_(\d+)$", label)
        if match:
            idx = match.group(1)
            return str(self.id2intent.get(idx, label))
        return label

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        raw_entities = self.ner_pipe(text, aggregation_strategy="simple")
        extracted: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for ent in raw_entities:
            entity_name = str(ent.get("entity_group", "")).strip()
            value = str(ent.get("word", "")).strip()
            confidence = float(ent.get("score", 0.0))
            if not entity_name or not value:
                continue
            if self.allowed_entities and entity_name not in self.allowed_entities:
                continue
            if confidence < settings.entity_min_confidence:
                continue
            normalized_value = self._normalize_entity_value(entity_name, value)
            key = (entity_name, normalized_value)
            if key in seen:
                continue
            seen.add(key)
            extracted.append(
                {
                    "entity": entity_name,
                    "value": value,
                    "start": int(ent.get("start", 0)),
                    "end": int(ent.get("end", 0)),
                    "confidence": confidence,
                    "normalized_value": normalized_value,
                    "provenance": "ml",
                }
            )

        return extracted

    @staticmethod
    def _normalize_entity_value(entity_name: str, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if entity_name == "region":
            return re.sub(r"\s*-\s*", "-", cleaned).lower()
        if entity_name == "app_name":
            return cleaned.lower()
        return cleaned


def save_model_artifacts(
    output_dir: str,
    intent_model: Any,
    intent_tokenizer: Any,
    ner_model: Any,
    ner_tokenizer: Any,
    metadata: Dict[str, Any],
) -> None:
    base = Path(output_dir)
    intent_dir = base / "intent"
    ner_dir = base / "ner"
    intent_dir.mkdir(parents=True, exist_ok=True)
    ner_dir.mkdir(parents=True, exist_ok=True)

    intent_model.save_pretrained(intent_dir)
    intent_tokenizer.save_pretrained(intent_dir)
    ner_model.save_pretrained(ner_dir)
    ner_tokenizer.save_pretrained(ner_dir)
    (base / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_model(model_path: str) -> NLUModel:
    base = Path(model_path)
    intent_dir = base / "intent"
    ner_dir = base / "ner"
    metadata_path = base / "metadata.json"

    if not intent_dir.exists() or not ner_dir.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Missing model artifacts in {model_path}. Expected intent/, ner/, and metadata.json"
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    id2intent = metadata.get("id2intent", {})
    allowed_entities = metadata.get("allowed_entities", [])
    model_version = metadata.get("model_version", settings.nlu_model_version)
    language_profile = metadata.get("language_profile", settings.nlu_language_profile)
    calibration = metadata.get("calibration", {})
    temperature = float(calibration.get("temperature", 1.0))

    intent_pipe = pipeline(
        "text-classification",
        model=str(intent_dir),
        tokenizer=str(intent_dir),
        device=-1,
    )
    ner_pipe = pipeline(
        "token-classification",
        model=str(ner_dir),
        tokenizer=str(ner_dir),
        device=-1,
    )

    return NLUModel(
        intent_pipe=intent_pipe,
        ner_pipe=ner_pipe,
        id2intent=id2intent,
        allowed_entities=allowed_entities,
        model_version=model_version,
        language_profile=language_profile,
        temperature=temperature,
    )


def parse_annotated_example(example: str) -> Tuple[str, List[Dict[str, Any]]]:
    entities: List[Dict[str, Any]] = []
    parts: List[str] = []
    cursor = 0

    for match in ANNOTATED_RE.finditer(example):
        parts.append(example[cursor:match.start()])
        value = match.group(1)
        entity = match.group(2)

        start = sum(len(part) for part in parts)
        parts.append(value)
        end = start + len(value)
        entities.append({"entity": entity, "value": value, "start": start, "end": end})

        cursor = match.end()

    parts.append(example[cursor:])
    clean = "".join(parts)
    return clean.strip(), entities


def convert_rasa_nlu(nlu_yml_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    content = yaml.safe_load(Path(nlu_yml_path).read_text(encoding="utf-8"))
    samples: List[Dict[str, Any]] = []
    known_values: Dict[str, set[str]] = {}

    for block in content.get("nlu", []):
        intent = block.get("intent")
        examples_blob = block.get("examples", "")
        for raw_line in examples_blob.splitlines():
            line = raw_line.strip()
            if not line.startswith("-"):
                continue
            example = line[1:].strip()
            if not example:
                continue
            plain_text, entities = parse_annotated_example(example)
            samples.append({"text": plain_text, "intent": intent, "entities": entities})
            for ent in entities:
                known_values.setdefault(ent["entity"], set()).add(str(ent["value"]))

    normalized_known_values = {
        key: sorted(values, key=lambda x: (len(x), x), reverse=True)
        for key, values in known_values.items()
    }
    return samples, normalized_known_values
