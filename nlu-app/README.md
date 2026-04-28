# NLU App (FastAPI + spaCy + scikit-learn)

Service NLU auto-hébergé, compatible avec le contrat Rasa `POST /model/parse`.

## Variables d'environnement

- `NLU_MODEL_PATH` (défaut `models/model.joblib`)
- `RASA_AUTH_TOKEN` (optionnel, pour compatibilité avec `api-app`)
- `NLU_AUTH_TOKEN` (optionnel, alias de `RASA_AUTH_TOKEN`)

## Entraînement

```bash
uv sync --frozen
uv run python scripts/train.py --input data.nlu.yml --output models/model.joblib
```

## Lancement local

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5005
```

## Procfile (Scalingo)

- `web`: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Endpoints

- `GET /status`
- `POST /model/parse`

### Exemple de payload

```json
{"text": "deploy my-app on osc-fr1 from https://github.com/user/repo branch main"}
```

### Exemple de réponse

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
