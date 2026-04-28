web: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2}
worker: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-1}
