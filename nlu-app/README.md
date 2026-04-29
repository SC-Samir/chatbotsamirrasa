# NLU App (FastAPI + Transformers CPU)

Service NLU auto-heberge, compatible avec le contrat Rasa `POST /model/parse`.

## Variables d'environnement

- `NLU_MODEL_PATH` (defaut `models`)
- `RASA_AUTH_TOKEN` (optionnel, pour compatibilite avec `api-app`)
- `NLU_AUTH_TOKEN` (optionnel, alias de `RASA_AUTH_TOKEN`)
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
  "intent": {"name": "deploy", "confidence": 0.91},
  "entities": [
    {"entity": "app_name", "value": "my-app"},
    {"entity": "region", "value": "osc-fr1"},
    {"entity": "github_repo", "value": "https://github.com/user/repo"},
    {"entity": "git_ref", "value": "main"}
  ],
  "text": "deploy my-app on osc-fr1 from https://github.com/user/repo branch main"
}
```

## Notes perf/taille

- Runtime CPU-only avec modeles compacts (`bert-tiny`) pour contenir la RAM et la taille image.
- Limiter le nombre de threads BLAS/OMP aide a stabiliser la latence en petit plan Scalingo.
