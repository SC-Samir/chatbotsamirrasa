from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

URL_RE = re.compile(r"https?://[^\s]+")
REGION_RE = re.compile(r"\b(osc-fr1|osc-secnum-fr1)\b", re.IGNORECASE)
APP_NAME_RE = re.compile(r"\b[a-z0-9][a-z0-9-]{2,29}\b")
BRANCH_RE = re.compile(r"\bbranch\s+([\w./-]+)", re.IGNORECASE)
TO_NUMBER_RE = re.compile(r"\bto\s+(\d{1,5})\b", re.IGNORECASE)
LINES_RE = re.compile(r"\b(\d{1,5})\s+lines\b", re.IGNORECASE)
FILTER_RE = re.compile(r"\b(?:with|filtered by)\s+([a-zA-Z0-9_-]+)\b", re.IGNORECASE)
CONTAINER_RE = re.compile(r"\b(web|worker)(?:-\d+)?\b", re.IGNORECASE)
CONTAINER_SIZE_RE = re.compile(r"\b(XXS|XS|S|M|L|XL|2XL)\b", re.IGNORECASE)


class NLUModel:
    def __init__(self, pipeline: Pipeline, known_values: Dict[str, List[str]], intent_keywords: Dict[str, List[str]]):
        self.pipeline = pipeline
        self.known_values = known_values
        self.intent_keywords = intent_keywords
        self._nlp = spacy.blank("en")
        self._ruler = self._nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
        patterns = []
        for entity_name, values in known_values.items():
            if entity_name in {"app_name", "github_repo", "git_ref", "container_amount", "n", "variable_value"}:
                continue
            for value in values[:1000]:
                if len(value.strip()) < 2:
                    continue
                patterns.append({"label": entity_name, "pattern": value})
        if patterns:
            self._ruler.add_patterns(patterns)

    def parse(self, text: str) -> Dict[str, Any]:
        normalized = text.strip()
        intent, confidence = self._predict_intent(normalized)
        entities = self._extract_entities(normalized)
        return {
            "intent": {"name": intent, "confidence": float(confidence)},
            "entities": entities,
            "text": text,
        }

    def _predict_intent(self, text: str) -> Tuple[str, float]:
        probs = self.pipeline.predict_proba([text])[0]
        classes = list(self.pipeline.classes_)
        best_idx = int(probs.argmax())
        ml_intent = classes[best_idx]
        ml_conf = float(probs[best_idx])

        low = text.lower()
        heuristics: List[Tuple[str, float]] = []
        for intent_name, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in low)
            if score > 0:
                heuristics.append((intent_name, min(0.95, 0.35 + 0.2 * score)))

        if heuristics:
            heur_intent, heur_conf = sorted(heuristics, key=lambda item: item[1], reverse=True)[0]
            if heur_conf > ml_conf + 0.12:
                return heur_intent, heur_conf

        return ml_intent, ml_conf

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        extracted: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        def add_entity(name: str, value: Any) -> None:
            as_str = str(value)
            key = (name, as_str)
            if key in seen:
                return
            seen.add(key)
            extracted.append({"entity": name, "value": value})

        for match in URL_RE.finditer(text):
            add_entity("github_repo", match.group(0).rstrip(".,;"))

        for match in REGION_RE.finditer(text):
            add_entity("region", match.group(1).lower())

        branch_match = BRANCH_RE.search(text)
        if branch_match:
            add_entity("git_ref", branch_match.group(1))

        line_match = LINES_RE.search(text)
        if line_match:
            add_entity("n", int(line_match.group(1)))

        scale_match = TO_NUMBER_RE.search(text)
        if scale_match and any(tok in text.lower() for tok in ["scale", "container", "instances"]):
            add_entity("container_amount", int(scale_match.group(1)))

        filter_match = FILTER_RE.search(text)
        if filter_match:
            add_entity("filter_param", filter_match.group(1))

        for match in CONTAINER_RE.finditer(text):
            add_entity("container_name", match.group(0))

        size_match = CONTAINER_SIZE_RE.search(text)
        if size_match:
            add_entity("container_size", size_match.group(1).upper())

        doc = self._nlp(text)
        for ent in doc.ents:
            add_entity(ent.label_, ent.text)

        # Prefer exact app-name matches from training values when present.
        known_app_names = self.known_values.get("app_name", [])
        low_text = text.lower()
        for known_name in known_app_names:
            candidate = known_name.strip()
            if not candidate:
                continue
            if candidate.lower() in low_text:
                add_entity("app_name", candidate)
                break

        tokens = text.split()
        if "app" in text.lower() and not any(e["entity"] == "app_name" for e in extracted):
            candidates = [tok.strip(".,;:()[]{}\"") for tok in tokens]
            for candidate in candidates:
                if APP_NAME_RE.fullmatch(candidate) and candidate.lower() not in {"scale", "deploy", "create", "delete", "restart", "rename"}:
                    if candidate.lower().startswith("osc-"):
                        continue
                    add_entity("app_name", candidate)
                    break

        return extracted


def train_model(samples: List[Tuple[str, str]], known_values: Dict[str, List[str]]) -> NLUModel:
    texts = [item[0] for item in samples]
    intents = [item[1] for item in samples]
    pipeline = Pipeline(
        [
            ("vectorizer", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipeline.fit(texts, intents)

    intent_keywords = {
        "deploy": ["deploy"],
        "create_and_deploy": ["create and deploy", "create app", "setup"],
        "show_context": ["context", "remember", "memory"],
        "get_logs": ["logs", "stream"],
        "restart": ["restart", "relaunch"],
        "scale": ["scale", "resize", "instances", "containers"],
        "delete_app": ["delete", "remove", "destroy", "terminate"],
        "rename_app": ["rename", "change the name", "update"],
        "list_env_vars": ["environment variables", "env vars", "variables"],
        "add_env_var": ["add", "set", "create", "variable"],
    }

    return NLUModel(pipeline=pipeline, known_values=known_values, intent_keywords=intent_keywords)


def save_model(model: NLUModel, output_path: str) -> None:
    payload = {
        "pipeline": model.pipeline,
        "known_values": model.known_values,
        "intent_keywords": model.intent_keywords,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, output)


def load_model(model_path: str) -> NLUModel:
    payload = joblib.load(model_path)
    return NLUModel(
        pipeline=payload["pipeline"],
        known_values=payload.get("known_values", {}),
        intent_keywords=payload.get("intent_keywords", {}),
    )


def parse_annotated_example(example: str) -> Tuple[str, List[Dict[str, str]]]:
    entities: List[Dict[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        value = match.group(1)
        entity = match.group(2)
        entities.append({"entity": entity, "value": value})
        return value

    clean = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", repl, example)
    return clean.strip(), entities


def convert_rasa_nlu(nlu_yml_path: str) -> Tuple[List[Tuple[str, str]], Dict[str, List[str]]]:
    import yaml

    content = yaml.safe_load(Path(nlu_yml_path).read_text(encoding="utf-8"))
    samples: List[Tuple[str, str]] = []
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
            samples.append((plain_text, intent))
            for ent in entities:
                known_values.setdefault(ent["entity"], set()).add(str(ent["value"]))

    normalized_known_values = {
        key: sorted(values, key=lambda x: (len(x), x), reverse=True)
        for key, values in known_values.items()
    }
    return samples, normalized_known_values
