#!/bin/bash
set -e

echo "=========================================="
echo "FluxCaption Backend Startup"
echo "=========================================="

# Run database migrations automatically
echo ""
echo "[1/3] Running database migrations..."
alembic upgrade head || {
    echo "❌ Database migration failed!"
    exit 1
}
echo "✅ Database migrations completed"

# Start Celery worker in background with optimized concurrency
echo ""
echo "[2/3] Starting Celery worker..."
celery -A app.workers.celery_app worker -l INFO -Q translate,scan,asr --concurrency=2 &
echo "✅ Celery worker started"

# Start FastAPI application (this will run in foreground)
echo ""
echo "[3/3] Starting FastAPI application..."
echo "=========================================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
