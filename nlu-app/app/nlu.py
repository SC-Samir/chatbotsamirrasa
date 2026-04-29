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
        top1 = ranking[0] if ranking else {"name": "nlu_fallback", "confidence_raw": 0.0, "confidence_calibrated": 0.0}
        top2 = ranking[1] if len(ranking) > 1 else {"confidence_calibrated": 0.0}
        margin = float(top1["confidence_calibrated"] - top2["confidence_calibrated"])

        min_conf_passed = float(top1["confidence_calibrated"]) >= settings.intent_min_confidence
        min_margin_passed = margin >= settings.intent_min_margin
        accepted_intent = top1["name"]
        reason = "accepted"
        if not min_conf_passed:
            accepted_intent = "nlu_fallback"
            reason = "low_confidence"
        elif not min_margin_passed:
            accepted_intent = "nlu_fallback"
            reason = "low_margin"

        entities = self._extract_entities(normalized)
        return {
            "intent_top1": top1,
            "intent_ranking": ranking[: max(1, settings.intent_topk)],
            "decision": {
                "accepted_intent": accepted_intent,
                "reason": reason,
                "min_conf_passed": bool(min_conf_passed),
                "min_margin_passed": bool(min_margin_passed),
                "margin": margin,
            },
            "entities": entities,
            "text_normalized": normalized,
            "model_info": {
                "version": self.model_version,
                "language_profile": self.language_profile,
            },
        }

    def _calibrate_score(self, score: float) -> float:
        if not settings.nlu_calibration_enabled:
            return float(score)
        # Temperature scaling approximation over model confidence.
        score = min(max(float(score), 1e-6), 1.0 - 1e-6)
        logit = math.log(score / (1.0 - score))
        calibrated = 1.0 / (1.0 + math.exp(-(logit / self.temperature)))
        return float(calibrated)

    def _predict_intents(self, text: str) -> List[Dict[str, float | str]]:
        results = self.intent_pipe(text, truncation=True, max_length=128, top_k=None)
        ranking: List[Dict[str, float | str]] = []
        for result in results:
            label = str(result.get("label", ""))
            intent_name = self.id2intent.get(label, label)
            raw_score = float(result.get("score", 0.0))
            ranking.append(
                {
                    "name": intent_name,
                    "confidence_raw": raw_score,
                    "confidence_calibrated": self._calibrate_score(raw_score),
                }
            )
        ranking.sort(key=lambda item: float(item["confidence_calibrated"]), reverse=True)
        return ranking

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
                    "confidence": confidence,
                    "normalized_value": normalized_value,
                }
            )

        return extracted

    @staticmethod
    def _normalize_entity_value(entity_name: str, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if entity_name == "region":
            return cleaned.lower()
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
