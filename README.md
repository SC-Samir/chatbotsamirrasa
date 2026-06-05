# chatbotsamirrasa Monorepo

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un monorepo contenant deux applications déployables indépendamment pour la gestion intelligente des déploiements Scalingo.

## 📦 Structure du Projet

```
chatbotsamirrasa/
├── api-app/          # Backend API avec FastAPI + WebSocket + Celery
│   ├── app/          # Code source
│   │   ├── copilot/  # Moteur de dialogue et orchestration
│   │   ├── domain/   # Modèles de domaine (Clean Architecture)
│   │   ├── application/ # Cas d'utilisation
│   │   ├── infrastructure/ # Adaptateurs externes
│   │   └── ...
│   ├── tests/        # Tests unitaires et d'intégration
│   └── pyproject.toml
│
└── nlu-app/          # Service NLU auto-hébergé
    ├── app/          # Code source
    │   ├── main.py   # Point d'entrée FastAPI
    │   ├── nlu.py    # Moteur de traitement du langage
    │   └── schemas.py # Schémas Pydantic
    ├── models/       # Modèles entrainés
    ├── scripts/      # Scripts d'entraînement
    └── pyproject.toml
```

## 🚀 Déploiement

### Prérequis

- Compte [Scalingo](https://scalingo.com) avec accès aux regions `osc-fr1` et `osc-secnum-fr1`
- Addon Redis (pour l'API app)
- Addon PostgreSQL (optionnel, pour la mémoire persistante)

### 1) Déployer le service NLU

```bash
cd nlu-app
scalingo --app chatbotsamir-nlu git-setup

# Variables d'environnement minimales
scalingo --app chatbotsamir-nlu env-set \
  NLU_MODEL_PATH=models \
  NLU_CONTRACT_VERSION=v3 \
  NLU_MODEL_VERSION=2026-05-04-v3d \
  NLU_LANGUAGE_PROFILE=fr_en_mixed \
  INTENT_MIN_CONFIDENCE=0.45 \
  INTENT_MIN_MARGIN=0.08 \
  INTENT_TOPK=3 \
  ENTITY_MIN_CONFIDENCE=0.00 \
  NLU_CALIBRATION_ENABLED=true

# Optionnel: sécuriser l'API NLU (compatible token Rasa)
scalingo --app chatbotsamir-nlu env-set RASA_AUTH_TOKEN=change-me

# Déploiement
git push scalingo main
```

### 2) Déployer l'API

```bash
cd api-app
scalingo --app chatbotsamir-api git-setup

scalingo --app chatbotsamir-api env-set \
  SCALINGO_API_TOKEN=xxx \
  REDIS_URL=redis://... \
  RASA_URL=https://chatbotsamir-nlu.osc-fr1.scalingo.io \
  RASA_TIMEOUT_MS=3000 \
  RASA_AUTH_TOKEN=change-me \
  NLU_EXPECTED_CONTRACT=v3 \
  NLU_FALLBACK_ENABLE_REGEX=true \
  NLU_CLARIFICATION_TOPK=3 \
  WEB_CONCURRENCY=2 \
  CELERY_CONCURRENCY=1 \
  DEBUG=false

# Déploiement
git push scalingo main
scalingo --app chatbotsamir-api scale worker:1
```

## ✅ Vérifications Post-Déploiement

- **NLU**: `GET /status` et `POST /model/parse`
- **API**: `/`, `/docs`, `/ws` (WebSocket)
- **Intégration**: Test end-to-end via WebSocket avec reconnaissance d'intents

## 📝 Développement Local

### Prérequis

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (gestionnaire de dépendances)

### Setup

```bash
# Pour api-app
cd api-app
uv sync
cp .env.example .env
# Éditer .env avec vos configurations

# Pour nlu-app
cd nlu-app
uv sync
cp .env.example .env  # si existe
```

### Lancement

**API App:**
```bash
cd api-app
# Serveur HTTP
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Worker Celery (dans un autre terminal)
uv run celery -A app.tasks.celery_app worker --loglevel=info
```

**NLU App:**
```bash
cd nlu-app
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5005
```

## 🧪 Tests

```bash
# Exécuter tous les tests
cd api-app
.venv/bin/python -m pytest tests/ -v

# Avec couverture
.venv/bin/python -m pytest tests/ --cov=app --cov-report=term
```

## 🏗️ Architecture

L'application suit les principes de **Clean Architecture** :

```
┌─────────────────────────────────────────┐
│              Presentation                │  (FastAPI, WebSocket)
├─────────────────────────────────────────┤
│              Application                 │  (Use Cases, DTOs)
├─────────────────────────────────────────┤
│               Domain                      │  (Entities, Value Objects)
├─────────────────────────────────────────┤
│            Infrastructure                 │  (Scalingo API, Rasa, Redis)
└─────────────────────────────────────────┘
```

- **Presentation**: Gère les requêtes HTTP/WebSocket
- **Application**: Contient la logique métier et les cas d'utilisation
- **Domain**: Modèles de domaine purs, indépendants des frameworks
- **Infrastructure**: Implémentations concrètes des ports (adaptateurs)

## 🔄 Migration vers NLU v3

### Ordre recommandé

1. Déployer `chatbotsamir-nlu` avec variables `NLU_*` et `INTENT_*`
2. Vérifier `POST /model/parse` avec header `X-NLU-Contract: v3`
3. Déployer `chatbotsamir-api` avec `NLU_EXPECTED_CONTRACT=v3`
4. Vérifier le handshake et les flows WebSocket
5. Retirer les anciennes hypothèses de payload legacy côté consommateurs

## 💃 Contribution

1. Forker le dépôt
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Commiter vos changements (`git commit -am 'Ajout de ma fonctionnalite'`)
4. Pousser vers la branche (`git push origin feature/ma-fonctionnalite`)
5. Ouvrir une Pull Request

## 🚨 Rollback

En cas de problème, rétablir l'ancien moteur Rasa via:

- `RASA_URL=https://chatbotsamir-rasa....scalingo.io`
- Redéployer `chatbotsamir-api`

## 📄 Licence

MIT License - voir [LICENSE](LICENSE) pour plus de détails.
