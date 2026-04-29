# chatbotsamirrasa monorepo

Ce repo est séparé en deux apps déployables indépendamment:

- `api-app/`: FastAPI + WebSocket + Celery (métier)
- `nlu-app/`: service NLU auto-hébergé (compatible `POST /model/parse`)

Le moteur NLU actif est `nlu-app/` (contrat v2).

## Déploiement Scalingo

### 1) Déployer NLU

```bash
cd nlu-app
scalingo --app chatbotsamir-nlu git-setup

# variables minimales
scalingo --app chatbotsamir-nlu env-set \
  NLU_MODEL_PATH=models \
  NLU_CONTRACT_VERSION=v2 \
  NLU_MODEL_VERSION=2026-04-29 \
  NLU_LANGUAGE_PROFILE=fr_en_mixed \
  INTENT_MIN_CONFIDENCE=0.60 \
  INTENT_MIN_MARGIN=0.15 \
  INTENT_TOPK=3 \
  ENTITY_MIN_CONFIDENCE=0.00 \
  NLU_CALIBRATION_ENABLED=true

# optionnel: sécuriser l'API NLU (compatible token Rasa)
scalingo --app chatbotsamir-nlu env-set RASA_AUTH_TOKEN=change-me

git push scalingo main
```

### 2) Déployer API

```bash
cd api-app
scalingo --app chatbotsamir-api git-setup

scalingo --app chatbotsamir-api env-set \
  SCALINGO_API_TOKEN=xxx \
  REDIS_URL=redis://... \
  RASA_URL=https://chatbotsamir-nlu.osc-fr1.scalingo.io \
  RASA_TIMEOUT_MS=3000 \
  RASA_AUTH_TOKEN=change-me \
  NLU_EXPECTED_CONTRACT=v2 \
  NLU_FALLBACK_ENABLE_REGEX=true \
  NLU_CLARIFICATION_TOPK=3 \
  WEB_CONCURRENCY=2 \
  CELERY_CONCURRENCY=1 \
  DEBUG=false

git push scalingo main
scalingo --app chatbotsamir-api scale worker:1
```

## Vérifications

- NLU: `GET /status` et `POST /model/parse`
- API: `/`, `/docs`, `/ws`
- End-to-end websocket + intents métiers

## Migration Breaking v2 (ordre recommande)

1. Deployer `chatbotsamir-nlu` avec variables `NLU_*` et `INTENT_*`.
2. Verifier `POST /model/parse` avec header `X-NLU-Contract: v2`.
3. Deployer `chatbotsamir-api` avec `NLU_EXPECTED_CONTRACT=v2`.
4. Verifier le handshake et les flows WebSocket.
5. Retirer ensuite les anciennes hypothèses de payload legacy cote consommateurs.

## Rollback rapide

Si besoin, remettre l'ancien moteur Rasa via:

- `RASA_URL=https://chatbotsamir-rasa....scalingo.io`
- redéployer `chatbotsamir-api`
