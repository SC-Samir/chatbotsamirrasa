from __future__ import annotations

import argparse
import json
import os
<<<<<<< HEAD
=======
import random
>>>>>>> c4c918e (samir)
import shutil
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

from app.nlu import convert_rasa_nlu, save_model_artifacts


@dataclass
class NERPrepared:
    encodings: Dict[str, List[List[int]]]
    labels: List[List[int]]


def build_intent_dataset(samples: List[Dict[str, Any]]) -> tuple[Dataset, Dict[str, int], Dict[str, str]]:
    intents = sorted({sample["intent"] for sample in samples})
    intent2id = {intent: idx for idx, intent in enumerate(intents)}
    id2intent = {str(idx): intent for intent, idx in intent2id.items()}

    rows = {
        "text": [sample["text"] for sample in samples],
        "label": [intent2id[sample["intent"]] for sample in samples],
    }
    return Dataset.from_dict(rows), intent2id, id2intent


def build_ner_tags(samples: List[Dict[str, Any]]) -> List[str]:
    entity_types = sorted({ent["entity"] for sample in samples for ent in sample["entities"]})
    tags = ["O"]
    for entity in entity_types:
        tags.append(f"B-{entity}")
        tags.append(f"I-{entity}")
    return tags


def prepare_ner_dataset(samples: List[Dict[str, Any]], tokenizer: Any, label2id: Dict[str, int], max_length: int) -> Dataset:
    tokenized = tokenizer(
        [sample["text"] for sample in samples],
        truncation=True,
        max_length=max_length,
        return_offsets_mapping=True,
    )

    all_labels: List[List[int]] = []

    for i, sample in enumerate(samples):
        offsets = tokenized["offset_mapping"][i]
        word_ids = tokenized.word_ids(batch_index=i)

        labels: List[int] = []
        previous_word_idx = None

        for token_idx, offset in enumerate(offsets):
            word_idx = word_ids[token_idx]
            if word_idx is None:
                labels.append(-100)
                continue
            if word_idx == previous_word_idx:
                labels.append(-100)
                continue

            start, end = offset
            label_name = "O"
            for ent in sample["entities"]:
                ent_start = int(ent["start"])
                ent_end = int(ent["end"])
                if start >= ent_start and end <= ent_end:
                    if start == ent_start:
                        label_name = f"B-{ent['entity']}"
                    else:
                        label_name = f"I-{ent['entity']}"
                    break

            labels.append(label2id[label_name])
            previous_word_idx = word_idx

        all_labels.append(labels)

    tokenized.pop("offset_mapping")
    tokenized["labels"] = all_labels
    return Dataset.from_dict(tokenized)


def compute_intent_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> Dict[str, float]:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    accuracy = float((preds == labels).mean())
    labels = labels.astype(int)
    preds = preds.astype(int)
    classes = sorted(set(labels.tolist()))

    f1_scores: List[float] = []
    for cls in classes:
        tp = int(((preds == cls) & (labels == cls)).sum())
        fp = int(((preds == cls) & (labels != cls)).sum())
        fn = int(((preds != cls) & (labels == cls)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        f1_scores.append(float(f1))
    macro_f1 = float(sum(f1_scores) / len(f1_scores)) if f1_scores else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1}


def compute_ner_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> Dict[str, float]:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    valid_true = 0
    valid_total = 0
    for pred_row, label_row in zip(predictions, labels):
        for pred, gold in zip(pred_row, label_row):
            if gold == -100:
                continue
            valid_total += 1
            if pred == gold:
                valid_true += 1

    token_accuracy = float(valid_true / valid_total) if valid_total else 0.0
    return {"token_accuracy": token_accuracy}


def _safe_train_eval_split(dataset: Dataset) -> tuple[Dataset, Dataset]:
    if len(dataset) < 10:
        return dataset, dataset
    try:
        split = dataset.class_encode_column("label").train_test_split(
            test_size=0.2,
            seed=42,
            stratify_by_column="label",
        )
    except Exception:
        split = dataset.train_test_split(test_size=0.2, seed=42)
    return split["train"], split["test"]


def train_intent_model(dataset: Dataset, output_dir: str, epochs: int, max_length: int, base_model: str):
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    label_names = sorted(set(dataset["label"]))
    num_labels = len(label_names)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=num_labels)

    train_ds, eval_ds = _safe_train_eval_split(dataset)
    tokenized_train = train_ds.map(
        lambda batch: tokenizer(batch["text"], truncation=True, max_length=max_length),
        batched=True,
    )
    tokenized_eval = eval_ds.map(
        lambda batch: tokenizer(batch["text"], truncation=True, max_length=max_length),
        batched=True,
    )

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=epochs,
<<<<<<< HEAD
        learning_rate=2e-5,
=======
        learning_rate=3e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
>>>>>>> c4c918e (samir)
        logging_steps=10,
        save_strategy="no",
        eval_strategy="epoch",
        report_to=[],
        dataloader_num_workers=0,
<<<<<<< HEAD
=======
        seed=42,
>>>>>>> c4c918e (samir)
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_intent_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()
    return model, tokenizer, metrics


def train_ner_model(samples: List[Dict[str, Any]], output_dir: str, epochs: int, max_length: int, base_model: str):
    labels = build_ner_tags(samples)
    label2id = {label: idx for idx, label in enumerate(labels)}
    id2label = {idx: label for label, idx in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForTokenClassification.from_pretrained(
        base_model,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

<<<<<<< HEAD
    pivot = int(max(1, len(samples) * 0.8))
    train_samples = samples[:pivot]
    eval_samples = samples[pivot:] or samples[:1]
=======
    shuffled_samples = samples[:]
    random.Random(42).shuffle(shuffled_samples)
    pivot = int(max(1, len(shuffled_samples) * 0.8))
    train_samples = shuffled_samples[:pivot]
    eval_samples = shuffled_samples[pivot:] or shuffled_samples[:1]
>>>>>>> c4c918e (samir)
    tokenized_train_dataset = prepare_ner_dataset(train_samples, tokenizer, label2id, max_length)
    tokenized_eval_dataset = prepare_ner_dataset(eval_samples, tokenizer, label2id, max_length)

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=epochs,
<<<<<<< HEAD
        learning_rate=2e-5,
=======
        learning_rate=3e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
>>>>>>> c4c918e (samir)
        logging_steps=10,
        save_strategy="no",
        eval_strategy="epoch",
        report_to=[],
        dataloader_num_workers=0,
<<<<<<< HEAD
=======
        seed=42,
>>>>>>> c4c918e (samir)
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_eval_dataset,
        data_collator=DataCollatorForTokenClassification(tokenizer=tokenizer),
        compute_metrics=compute_ner_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()
    return model, tokenizer, labels, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Transformers NLU model from Rasa NLU YAML")
    parser.add_argument("--input", required=True, help="Path to Rasa-style nlu.yml")
    parser.add_argument("--output", default="models", help="Path to output model directory")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--max-length", type=int, default=128, help="Maximum sequence length")
<<<<<<< HEAD
    parser.add_argument("--base-model", default="prajjwal1/bert-tiny", help="HF base model for fine-tuning")
    parser.add_argument("--model-version", default="dev", help="Model version saved in metadata")
    parser.add_argument("--language-profile", default="fr_en_mixed", help="Language profile in metadata")
    parser.add_argument("--report-dir", default="reports", help="Training report output directory")
=======
    parser.add_argument("--base-model", default="xlm-roberta-base", help="HF base model for fine-tuning")
    parser.add_argument("--model-version", default="dev", help="Model version saved in metadata")
    parser.add_argument("--language-profile", default="fr_en_mixed", help="Language profile in metadata")
    parser.add_argument("--report-dir", default="reports", help="Training report output directory")
    parser.add_argument("--min-intent-macro-f1", type=float, default=0.80, help="Fail training if intent macro-f1 is below this threshold")
    parser.add_argument("--min-ner-token-accuracy", type=float, default=0.90, help="Fail training if NER token accuracy is below this threshold")
>>>>>>> c4c918e (samir)
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    samples, known_values = convert_rasa_nlu(args.input)
    if not samples:
        raise SystemExit("No training samples found")

    intent_dataset, _intent2id, id2intent = build_intent_dataset(samples)

    intent_model, intent_tokenizer, intent_metrics = train_intent_model(
        dataset=intent_dataset,
        output_dir=f"{args.output}/_intent_training",
        epochs=args.epochs,
        max_length=args.max_length,
        base_model=args.base_model,
    )

    ner_model, ner_tokenizer, ner_labels, ner_metrics = train_ner_model(
        samples=samples,
        output_dir=f"{args.output}/_ner_training",
        epochs=args.epochs,
        max_length=args.max_length,
        base_model=args.base_model,
    )

    metadata = {
        "id2intent": id2intent,
        "allowed_entities": sorted({label[2:] for label in ner_labels if label.startswith(("B-", "I-"))}),
        "base_model": args.base_model,
        "epochs": args.epochs,
        "max_length": args.max_length,
        "num_samples": len(samples),
        "known_values": known_values,
        "model_version": args.model_version,
        "language_profile": args.language_profile,
        "calibration": {"temperature": 1.0},
    }

    save_model_artifacts(
        output_dir=args.output,
        intent_model=intent_model,
        intent_tokenizer=intent_tokenizer,
        ner_model=ner_model,
        ner_tokenizer=ner_tokenizer,
        metadata=metadata,
    )
    shutil.rmtree(f"{args.output}/_intent_training", ignore_errors=True)
    shutil.rmtree(f"{args.output}/_ner_training", ignore_errors=True)
    os.makedirs(args.report_dir, exist_ok=True)
    report = {
        "intent_metrics": intent_metrics,
        "ner_metrics": ner_metrics,
        "num_samples": len(samples),
        "base_model": args.base_model,
        "model_version": args.model_version,
        "language_profile": args.language_profile,
    }
<<<<<<< HEAD
    with open(f"{args.report_dir}/training_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

=======

    intent_macro_f1 = float(intent_metrics.get("eval_macro_f1", intent_metrics.get("macro_f1", 0.0)))
    ner_token_accuracy = float(ner_metrics.get("eval_token_accuracy", ner_metrics.get("token_accuracy", 0.0)))
    gates = {
        "intent_macro_f1": {"value": intent_macro_f1, "min_required": args.min_intent_macro_f1},
        "ner_token_accuracy": {"value": ner_token_accuracy, "min_required": args.min_ner_token_accuracy},
    }
    report["quality_gates"] = gates

    with open(f"{args.report_dir}/training_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    failed = []
    if intent_macro_f1 < args.min_intent_macro_f1:
        failed.append(
            f"intent macro-f1 {intent_macro_f1:.4f} < required {args.min_intent_macro_f1:.4f}"
        )
    if ner_token_accuracy < args.min_ner_token_accuracy:
        failed.append(
            f"ner token accuracy {ner_token_accuracy:.4f} < required {args.min_ner_token_accuracy:.4f}"
        )
    if failed:
        raise SystemExit("Quality gate failure: " + "; ".join(failed))

>>>>>>> c4c918e (samir)
    print(f"Model saved to {args.output} with {len(samples)} samples")


if __name__ == "__main__":
    main()
