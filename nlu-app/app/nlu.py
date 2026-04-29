from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from transformers import pipeline

ANNOTATED_RE = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")


class NLUModel:
    def __init__(
        self,
        intent_pipe: Any,
        ner_pipe: Any,
        id2intent: Dict[str, str],
        allowed_entities: List[str],
    ):
        self.intent_pipe = intent_pipe
        self.ner_pipe = ner_pipe
        self.id2intent = id2intent
        self.allowed_entities = set(allowed_entities)

    def parse(self, text: str) -> Dict[str, Any]:
        normalized = text.strip()
        intent_name, confidence = self._predict_intent(normalized)
        entities = self._extract_entities(normalized)
        return {
            "intent": {"name": intent_name, "confidence": float(confidence)},
            "entities": entities,
            "text": text,
        }

    def _predict_intent(self, text: str) -> Tuple[str, float]:
        result = self.intent_pipe(text, truncation=True, max_length=128)[0]
        label = str(result.get("label", ""))
        intent_name = self.id2intent.get(label, label)
        return intent_name, float(result.get("score", 0.0))

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        raw_entities = self.ner_pipe(text, aggregation_strategy="simple")
        extracted: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for ent in raw_entities:
            entity_name = str(ent.get("entity_group", "")).strip()
            value = str(ent.get("word", "")).strip()
            if not entity_name or not value:
                continue
            if self.allowed_entities and entity_name not in self.allowed_entities:
                continue
            key = (entity_name, value)
            if key in seen:
                continue
            seen.add(key)
            extracted.append({"entity": entity_name, "value": value})

        return extracted


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
