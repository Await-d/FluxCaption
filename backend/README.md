# FluxCaption Backend

AI-powered subtitle translation system backend built with FastAPI and Celery.

## Quick Start

### Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your configuration
   ```

3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start the API server:**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Start Celery worker:**
   ```bash
   celery -A app.workers.celery_app worker -l INFO
   ```

6. **Start Celery beat (optional):**
   ```bash
   celery -A app.workers.celery_app beat -l INFO
   ```

### Docker Setup

```bash
docker-compose up -d
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/routers/       # API endpoints
│   ├── core/              # Core configuration
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   └── workers/           # Celery tasks
├── migrations/            # Alembic migrations
└── tests/                 # Test suite
```

## Key Features

- ✅ Multi-database support (PostgreSQL, MySQL, SQLite, SQL Server)
- ✅ Async API with FastAPI
- ✅ Distributed task processing with Celery
- ✅ Ollama integration for LLM inference
- ✅ SSE for real-time progress updates
- ✅ Structured JSON logging

## Environment Variables

See `../.env.example` for all configuration options.

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run with coverage
pytest --cov=app tests/
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## License

MIT
