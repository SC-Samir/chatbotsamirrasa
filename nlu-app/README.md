# NLU App (FastAPI + Transformers CPU)

Service NLU auto-heberge expose en contrat **NLU v3** sur `POST /model/parse`.

## Variables d'environnement

- `NLU_MODEL_PATH` (defaut `models`)
- `RASA_AUTH_TOKEN` (optionnel, pour compatibilite avec `api-app`)
- `NLU_AUTH_TOKEN` (optionnel, alias de `RASA_AUTH_TOKEN`)
- `NLU_CONTRACT_VERSION` (defaut `v3`)
- `NLU_MODEL_VERSION` (ex: `2026-05-04-v3d`)
- `NLU_LANGUAGE_PROFILE` (defaut `fr_en_mixed`)
- `INTENT_MIN_CONFIDENCE` (defaut `0.45`)
- `INTENT_MIN_MARGIN` (defaut `0.08`)
- `INTENT_TOPK` (defaut `3`)
- `ENTITY_MIN_CONFIDENCE` (defaut `0.0`)
- `NLU_CALIBRATION_ENABLED` (defaut `true`)
- `TOKENIZERS_PARALLELISM` (recommande `false` en prod)
- `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` (recommande `1` en CPU contraint)

## Entrainement

```bash
uv sync
uv run python scripts/train.py --input data.nlu.yml --output models --epochs 3 --max-length 128 --base-model prajjwal1/bert-tiny
```

Artefacts generes:

- `models/intent/*`
- `models/ner/*`
- `models/metadata.json`

## Lancement local

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5005
```

## Docker

Build:

```bash
docker build -t chatbotsamir-nlu .
```

Run:

```bash
docker run --rm -p 5005:8000 -e NLU_MODEL_PATH=models chatbotsamir-nlu
```

## Endpoints

- `GET /status`
- `POST /model/parse`

### Exemple de payload

```json
{"text": "deploy my-app on osc-fr1 from https://github.com/user/repo branch main"}
```

### Exemple de reponse

```json
{
  "hypotheses": [
    {"name": "deploy", "confidence": 0.9, "confidence_calibrated": 0.91, "rank": 1, "rationale_features": {"raw_confidence": 0.9}},
    {"name": "create_and_deploy", "confidence": 0.07, "confidence_calibrated": 0.05, "rank": 2, "rationale_features": {"raw_confidence": 0.07}},
    {"name": "show_context", "confidence": 0.03, "confidence_calibrated": 0.02, "rank": 3, "rationale_features": {"raw_confidence": 0.03}}
  ],
  "final_decision": {
    "action": "accept",
    "intent": "deploy",
    "reason": "accepted",
    "policy": {"min_confidence_threshold": 0.6, "min_margin_threshold": 0.15, "min_conf_passed": true, "min_margin_passed": true},
    "margin": 0.86
  },
  "entities": [
    {"entity": "app_name", "value": "my-app", "start": 7, "end": 13, "confidence": 0.99, "normalized_value": "my-app", "provenance": "ml"},
    {"entity": "region", "value": "osc-fr1", "start": 17, "end": 24, "confidence": 0.99, "normalized_value": "osc-fr1", "provenance": "ml"}
  ],
  "quality_signals": {"ambiguity_score": 0.14, "ood_likelihood": 0.09, "calibration_band": "high"},
  "text_normalized": "deploy my-app on osc-fr1 from https://github.com/user/repo branch main",
  "model_info": {"version": "2026-04-29", "language_profile": "fr_en_mixed"}
}
```

## Notes perf/taille

- Runtime CPU-only avec modeles compacts (`bert-tiny`) pour contenir la RAM et la taille image.
- Limiter le nombre de threads BLAS/OMP aide a stabiliser la latence en petit plan Scalingo.
