web: uvicorn app.main:app --host 0.0.0.0 --port $port
worker: celery -A app.tasks.celery_app worker --loglevel=info