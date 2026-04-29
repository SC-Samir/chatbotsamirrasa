from __future__ import annotations

import argparse
import os
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
    return {"accuracy": accuracy}


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


def train_intent_model(dataset: Dataset, output_dir: str, epochs: int, max_length: int, base_model: str):
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    label_names = sorted(set(dataset["label"]))
    num_labels = len(label_names)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=num_labels)

    tokenized = dataset.map(
        lambda batch: tokenizer(batch["text"], truncation=True, max_length=max_length),
        batched=True,
    )

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=epochs,
        learning_rate=2e-5,
        logging_steps=10,
        save_strategy="no",
        eval_strategy="no",
        report_to=[],
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_intent_metrics,
    )
    trainer.train()
    return model, tokenizer


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

    tokenized_dataset = prepare_ner_dataset(samples, tokenizer, label2id, max_length)

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=epochs,
        learning_rate=2e-5,
        logging_steps=10,
        save_strategy="no",
        eval_strategy="no",
        report_to=[],
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForTokenClassification(tokenizer=tokenizer),
        compute_metrics=compute_ner_metrics,
    )
    trainer.train()
    return model, tokenizer, labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Transformers NLU model from Rasa NLU YAML")
    parser.add_argument("--input", required=True, help="Path to Rasa-style nlu.yml")
    parser.add_argument("--output", default="models", help="Path to output model directory")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--max-length", type=int, default=128, help="Maximum sequence length")
    parser.add_argument("--base-model", default="prajjwal1/bert-tiny", help="HF base model for fine-tuning")
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    samples, known_values = convert_rasa_nlu(args.input)
    if not samples:
        raise SystemExit("No training samples found")

    intent_dataset, _intent2id, id2intent = build_intent_dataset(samples)

    intent_model, intent_tokenizer = train_intent_model(
        dataset=intent_dataset,
        output_dir=f"{args.output}/_intent_training",
        epochs=args.epochs,
        max_length=args.max_length,
        base_model=args.base_model,
    )

    ner_model, ner_tokenizer, ner_labels = train_ner_model(
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

    print(f"Model saved to {args.output} with {len(samples)} samples")


if __name__ == "__main__":
    main()
