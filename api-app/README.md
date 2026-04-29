# API App (FastAPI + Celery)

Cette app expose l'API HTTP/WebSocket et délègue la compréhension des intents à un service NLU HTTP (par défaut `nlu-app`) via `RASA_URL`.

## Variables d'environnement

- `SCALINGO_API_TOKEN` (obligatoire)
- `REDIS_URL` (obligatoire)
- `RASA_URL` (défaut `http://localhost:5005`, doit pointer vers `chatbotsamir-nlu` en prod)
- `RASA_TIMEOUT_MS` (défaut `3000`)
- `RASA_AUTH_TOKEN` (optionnel, transmis au NLU en query param `token`)
- `NLU_EXPECTED_CONTRACT` (defaut `v2`, envoye en header `X-NLU-Contract`)
- `NLU_FALLBACK_ENABLE_REGEX` (defaut `true`)
- `NLU_CLARIFICATION_TOPK` (defaut `3`)
- `DEBUG` (défaut `false`)

## Lancement local

```bash
uv sync --frozen
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Worker:

```bash
uv run celery -A app.tasks.celery_app worker --loglevel=info
```

## Procfile (Scalingo)

- `web`: Gunicorn/Uvicorn sur `$PORT`
- `worker`: Celery
