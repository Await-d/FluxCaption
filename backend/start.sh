#!/bin/bash
set -e

# Start Celery worker in background with optimized concurrency
celery -A app.workers.celery_app worker -l INFO -Q translate,scan,asr --concurrency=2 &

# Start FastAPI application (this will run in foreground)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
