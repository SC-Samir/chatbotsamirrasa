# ScalingoOps Agent

Agent intelligent pour la gestion des déploiements et logs Scalingo via interface conversationnelle.

## 📋 Table des matières

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entraînement du modèle Rasa](#entraînement-du-modèle-rasa)
- [Lancement de l'application](#lancement-de-lapplication)
- [Utilisation de Celery](#utilisation-de-celery)
- [API Endpoints](#api-endpoints)
- [Développement](#développement)
- [Tests](#tests)
- [Déploiement](#déploiement)

## 🔧 Prérequis

- Python 3.10.12 (voir `runtime.txt`)
- Redis (pour Celery et Pub/Sub)
- Token API Scalingo
- Git

### Installation des prérequis système

#### macOS (avec Homebrew)
```bash
# Installer Redis
brew install redis

# Démarrer Redis
brew services start redis

# Vérifier que Redis fonctionne
redis-cli ping  # Doit répondre "PONG"
```

#### Ubuntu/Debian
```bash
# Installer Redis
sudo apt update
sudo apt install redis-server

# Démarrer Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Vérifier que Redis fonctionne
redis-cli ping  # Doit répondre "PONG"
```

## 🚀 Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd chatbotsamirrasa
```

2. **Installer `uv`**
```bash
python3 -m pip install uv
```

3. **Créer l'environnement et synchroniser les dépendances**
```bash
# Dépendances applicatives
uv sync --frozen

# Dépendances de dev/test (optionnel)
uv sync --frozen --group dev
```

## ⚙️ Configuration

1. **Créer le fichier `.env`**
```bash
# Renommer le fichier de template
mv .env_defaut .env
```

2. **Configurer les variables d'environnement dans `.env`**
```env
# Token API Scalingo (obligatoire)
SCALINGO_API_TOKEN=your_scalingo_api_token_here

# URL Redis (par défaut: redis://localhost:6379/0)
REDIS_URL=redis://localhost:6379/0

# Chemin vers le modèle Rasa (optionnel)
RASA_MODEL_PATH=models/model.tar.gz

# Mode debug (optionnel)
DEBUG=false
```

3. **Obtenir un token API Scalingo**
   - Aller sur [Scalingo Dashboard](https://dashboard.scalingo.com/)
   - Aller dans **Account** > **API Tokens**
   - Créer un nouveau token avec les permissions nécessaires

## 🧠 Entraînement du modèle Rasa

### Structure des données d'entraînement

Le modèle Rasa utilise les fichiers suivants :
- `data/nlu.yml` : Exemples d'intents et d'entités
- `domain.yml` : Configuration du domaine (intents, entités, réponses)
- `stories.yml` : Histoires de conversation
- `config.yml` : Configuration du pipeline ML

### Entraîner le modèle

1. **Entraîner le modèle NLU uniquement**
```bash
# Entraîner avec les données actuelles
uv run rasa train nlu --data data/ --config config.yml --out models/ --fixed-model-name model.tar.gz

# Le modèle sera sauvegardé dans models/ avec un nom généré automatiquement
```

2. **Entraîner le modèle complet (NLU + Core)**
```bash
# Entraîner le modèle complet
uv run rasa train --data data/ --config config.yml --domain domain.yml --out models/

# Vérifier les modèles générés
ls -la models/
```

3. **Mettre à jour le chemin du modèle dans la configuration**
```bash
# Copier le nom du modèle généré et mettre à jour app/config.py
# ou définir la variable d'environnement RASA_MODEL_PATH
```

### Validation des données

```bash
# Valider la structure des données
rasa data validate --data data/ --domain domain.yml

# Tester le modèle entraîné
rasa test --model models/ --test-stories tests/
```

## 🏃‍♂️ Lancement de l'application

### Mode développement

1. **Lancer Redis** (si pas déjà fait)
```bash
redis-server
```

2. **Lancer l'application FastAPI**
```bash
# Mode développement avec rechargement automatique
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ou avec Gunicorn pour la production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. **Accéder à l'application**
   - Interface web : http://localhost:8000
   - API docs : http://localhost:8000/docs
   - WebSocket : ws://localhost:8000/ws

### Mode production

```bash
# Utiliser le Procfile (pour Heroku/Scalingo)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

## 🔄 Utilisation de Celery

Celery est utilisé pour les tâches asynchrones comme le monitoring des déploiements.

### Lancer le worker Celery

1. **Dans un terminal séparé**
```bash
# Lancer le worker Celery
celery -A app.tasks.celery_app worker --loglevel=info

# Ou avec plus de workers
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# Lancer avec auto-reload en développement
celery -A app.tasks.celery_app worker --loglevel=info --reload
```

2. **Lancer le scheduler (optionnel)**
```bash
# Pour les tâches périodiques
celery -A app.tasks.celery_app beat --loglevel=info
```

3. **Monitorer Celery**
```bash
# Interface de monitoring (nécessite flower)
pip install flower
celery -A app.tasks.celery_app flower

# Accéder à l'interface : http://localhost:5555
```

### Tâches disponibles

- `poll_deployment_status` : Surveille le statut d'un déploiement
- Tâches personnalisées peuvent être ajoutées dans `app/tasks.py`

## 🌐 API Endpoints

### Endpoints REST

- `GET /` : Interface web principale
- `GET /docs` : Documentation interactive de l'API
- `GET /logs/{app_name}` : Récupération des logs d'une application
- `GET /logs/{app_name}/stream` : Streaming des logs (Server-Sent Events)
- `GET /logs/{app_name}/display` : Affichage formaté des logs

### WebSocket

- `WS /ws` : Interface conversationnelle avec l'agent Rasa

### Exemples d'utilisation

```bash
# Récupérer les logs d'une application
curl "http://localhost:8000/logs/my-app?region=osc-fr1&n=50"

# Stream des logs
curl "http://localhost:8000/logs/my-app/stream?region=osc-fr1"

# Affichage formaté des logs
curl "http://localhost:8000/logs/my-app/display?region=osc-fr1&n=100"
```

## 💬 Intents supportés

L'agent conversationnel supporte les intents suivants :

- `deploy` : Déploiement d'une application
- `create_and_deploy` : Création et déploiement d'une nouvelle application
- `get_logs` : Récupération des logs d'une application
- `show_context` : Affichage du contexte mémorisé
- `restart` : Redémarrage d'une application
- `scale` : Mise à l'échelle (modification du nombre de conteneurs et de leur taille)

### Exemples de conversations

```
Utilisateur: "Déploie mon application my-app"
Agent: "Je vais déployer votre application my-app..."

Utilisateur: "Montre-moi les logs de my-app"
Agent: "Voici les derniers logs de my-app..."

Utilisateur: "Redémarre my-app"
Agent: "Je redémarre votre application my-app..."
```

## 🛠️ Développement

### Structure du projet

```
app/
├── config.py              # Configuration centralisée
├── models.py              # Modèles de données Pydantic
├── main.py                # Point d'entrée FastAPI
├── scalingo_manager.py    # Gestionnaire API Scalingo
├── tasks.py               # Tâches Celery
├── services/              # Services métier
│   ├── logs_service.py    # Service de gestion des logs
│   └── app_management_service.py
├── handlers/              # Gestionnaires d'événements
│   ├── websocket_handler.py    # Gestionnaire WebSocket
│   ├── intent_handlers.py      # Handlers d'intents Rasa
│   └── app_management_handlers.py
├── middleware/            # Middlewares FastAPI
├── exceptions/            # Exceptions personnalisées
└── utils/                 # Utilitaires
```

### Ajouter un nouvel intent

1. **Ajouter l'intent dans `domain.yml`**
```yaml
intents:
  - new_intent
```

2. **Ajouter des exemples dans `data/nlu.yml`**
```yaml
- intent: new_intent
  examples: |
    - exemple de phrase 1
    - exemple de phrase 2
```

3. **Ajouter l'histoire dans `stories.yml`**
```yaml
- story: nouvelle histoire
  steps:
  - intent: new_intent
  - action: action_response
```

4. **Créer le handler dans `app/handlers/intent_handlers.py`**
```python
def handle_new_intent(self, tracker: Tracker) -> List[Dict]:
    # Logique de traitement
    return []
```

5. **Réentraîner le modèle**
```bash
uv run rasa train --data data/ --config config.yml --domain domain.yml --out models/
```

### Commandes utiles

```bash
# Tests
uv run pytest tests/ -v
uv run pytest tests/ --cov=app --cov-report=html
```

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests
uv run pytest tests/ -v

# Tests avec couverture
uv run pytest tests/ --cov=app --cov-report=html --cov-report=term

# Tests spécifiques
uv run pytest tests/test_models.py -v

# Tests avec logs détaillés
uv run pytest tests/ -v -s --log-cli-level=DEBUG
```

### Structure des tests

```
tests/
├── conftest.py           # Configuration pytest
├── test_models.py        # Tests des modèles Pydantic
└── test_services/        # Tests des services
```

## 🚀 Déploiement

### Déploiement sur Scalingo

1. **Préparer l'application**
```bash
# Créer un Procfile (déjà présent)
# web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
# worker: celery -A app.tasks.celery_app worker --loglevel=info

# Installer l'addon Redis
scalingo addons-add redis redis-sandbox
```

2. **Configurer les variables d'environnement**
```bash
scalingo env-set SCALINGO_API_TOKEN=your_token_here
scalingo env-set REDIS_URL=$REDIS_URL
```

3. **Déployer**
```bash
git push scalingo main
```

### Déploiement avec Docker

```bash
# 1) Construire les images
docker compose build

# 2) Entraîner le modèle Rasa via le Dockerfile dédié
docker compose --profile train run --rm rasa-train

# 3) Lancer l'application + worker + redis
docker compose up app worker redis

# 4) Arrêter les services
docker compose down
```

## 🔍 Monitoring et logs

### Logs de l'application

```bash
# Logs en temps réel
tail -f logs/app.log

# Logs Scalingo
scalingo logs --app your-app-name
```

### Monitoring des performances

- Utiliser Flower pour monitorer Celery : http://localhost:5555
- Logs structurés avec le système de logging intégré
- Métriques Redis avec `redis-cli info`

## 🆘 Dépannage

### Problèmes courants

1. **Erreur de connexion Redis**
```bash
# Vérifier que Redis fonctionne
redis-cli ping

# Redémarrer Redis
brew services restart redis  # macOS
sudo systemctl restart redis-server  # Linux
```

2. **Erreur de modèle Rasa**
```bash
# Vérifier que le modèle existe
ls -la models/

# Réentraîner le modèle
uv run rasa train --data data/ --config config.yml --domain domain.yml --out models/
```

3. **Erreur de token Scalingo**
```bash
# Vérifier la variable d'environnement
echo $SCALINGO_API_TOKEN

# Tester la connexion API
curl -H "Authorization: Bearer $SCALINGO_API_TOKEN" \
     https://api.osc-fr1.scalingo.com/v1/apps
```

### Support

- Consulter les logs de l'application
- Vérifier la documentation Scalingo API
- Consulter la documentation Rasa

## 📚 Ressources

- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation Rasa](https://rasa.com/docs/)
- [Documentation Celery](https://docs.celeryproject.org/)
- [Documentation Scalingo API](https://developers.scalingo.com/)
- [Documentation Redis](https://redis.io/documentation)
