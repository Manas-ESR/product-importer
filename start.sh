#!/usr/bin/env bash
set -e

echo "Starting Celery worker..."
python -m celery -A app.celery_app.celery_app worker --loglevel=info &

echo "Starting Uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
