# chatbotsamirrasa monorepo

Ce repo est maintenant séparé en deux apps déployables indépendamment:

- `api-app/`: FastAPI + WebSocket + Celery (léger)
- `rasa-app/`: service Rasa (NLU)

## Déploiement Scalingo

### 1) Déployer Rasa

```bash
cd rasa-app
scalingo --app chatbotsamir-rasa git-setup
# variables minimales
scalingo --app chatbotsamir-rasa env-set RASA_MODEL_PATH=models/model.tar.gz
# optionnel: sécuriser l'API rasa
scalingo --app chatbotsamir-rasa env-set RASA_AUTH_TOKEN=change-me

git push scalingo main
```

### 2) Déployer API

```bash
cd api-app
scalingo --app chatbotsamir-api git-setup

scalingo --app chatbotsamir-api env-set \
  SCALINGO_API_TOKEN=xxx \
  REDIS_URL=redis://... \
  RASA_URL=https://chatbotsamir-rasa.osc-fr1.scalingo.io \
  RASA_TIMEOUT_MS=3000 \
  RASA_AUTH_TOKEN=change-me \
  WEB_CONCURRENCY=2 \
  CELERY_CONCURRENCY=1 \
  DEBUG=false

git push scalingo main
scalingo --app chatbotsamir-api scale worker:1
```

## Vérifications

- Rasa: `GET /status`
- API: `/`, `/docs`, `/ws`
- End-to-end websocket + intents métiers
