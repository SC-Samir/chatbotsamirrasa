# Rasa App

Service Rasa indépendant pour l'inférence d'intents.

## Variables d'environnement

- `RASA_MODEL_PATH` (défaut `models/model.tar.gz`)
- `RASA_AUTH_TOKEN` (optionnel, recommandé)

## Lancement local

```bash
uv sync --frozen
rasa run --enable-api --host 0.0.0.0 --port 5005 --model models/model.tar.gz
```

## Procfile (Scalingo)

- `web`: `rasa run --enable-api --host 0.0.0.0 --port $PORT ...`

## Endpoints utiles

- `GET /status`
- `POST /model/parse`
