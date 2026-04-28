# chatbotsamirrasa monorepo

Ce repo est séparé en deux apps déployables indépendamment:

- `api-app/`: FastAPI + WebSocket + Celery (métier)
- `nlu-app/`: service NLU auto-hébergé (compatible `POST /model/parse`)

`rasa-app/` est conservé temporairement pour rollback.

## Déploiement Scalingo

### 1) Déployer NLU

```bash
cd nlu-app
scalingo --app chatbotsamir-nlu git-setup

# variables minimales
scalingo --app chatbotsamir-nlu env-set NLU_MODEL_PATH=models/model.joblib

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

## Rollback rapide

Si besoin, remettre l'ancien moteur Rasa via:

- `RASA_URL=https://chatbotsamir-rasa....scalingo.io`
- redéployer `chatbotsamir-api`
