# API App (FastAPI + Celery)

Cette app expose l'API HTTP/WebSocket et délègue la compréhension des intents à un service NLU HTTP (par défaut `nlu-app`) via `RASA_URL`.

## Variables d'environnement

- `SCALINGO_API_TOKEN` (obligatoire)
- `REDIS_URL` (obligatoire)
- `DATABASE_URL` (obligatoire pour `ws.v2` durable memory) ou `MEMORY_POSTGRES_DSN`
- `RASA_URL` (défaut `http://localhost:5005`, doit pointer vers `chatbotsamir-nlu` en prod)
- `RASA_TIMEOUT_MS` (défaut `3000`)
- `RASA_AUTH_TOKEN` (optionnel, transmis au NLU en query param `token`)
- `NLU_EXPECTED_CONTRACT` (defaut `v3`, envoye en header `X-NLU-Contract`)
- `NLU_FALLBACK_ENABLE_REGEX` (defaut `true`)
- `NLU_CLARIFICATION_TOPK` (defaut `3`)
- `MEMORY_SESSION_TTL_SECONDS` (defaut `3600`)
- `DEBUG` (défaut `false`)

## WebSocket v2 (breaking)

Le endpoint `/ws` est maintenant basé sur le contrat `ws.v2` et implémenté dans le module unifié `app/copilot/*` (les imports `app/v2/*` restent disponibles uniquement en compatibilité).

- `event_type`
- `status`
- `action_id`
- `human_message`
- `structured_payload`
- `next_actions`
- `risk_level`

Mémoire hybride:

- court-terme: Redis (session + confirmation tokens)
- long-terme: PostgreSQL (`memory_facts`, `memory_events`)

Command coverage reference: `SUPPORTED_COMMANDS.md`

Legacy stack toggle:

- WebSocket endpoint `/ws` is now strictly `ws.v2` (legacy `handlers/*` flow removed from runtime wiring).

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
