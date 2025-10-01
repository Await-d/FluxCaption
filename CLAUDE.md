# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Development Principles

**🚫 NO MOCK SOLUTIONS**
- All operations must use real data
- All monitoring data must come from real system metrics
- All terminal operations must be real container exec sessions

**🚫 NO SIMPLIFIED SOLUTIONS**
- Implement complete error handling and edge cases
- Implement complete performance optimization and caching mechanisms
- Implement complete security validation and permission control

**🚫 NO TEMPORARY SOLUTIONS**
- All implementations must be production-grade quality
- All code must be maintainable long-term
- All architecture must support future expansion needs

## Project Overview

FluxCaption is an AI-powered subtitle translation system for Jellyfin media libraries. The system automatically detects missing subtitle languages, performs ASR (Automatic Speech Recognition) on media without subtitles, and translates subtitles using local LLM models via Ollama.

**Tech Stack:**
- Backend: Python FastAPI + Celery + SQLAlchemy 2 + Alembic
- Frontend: React 19 + Vite + TypeScript + Tailwind CSS + Radix UI
- AI/Inference: Ollama (local LLM models)
- Storage: PostgreSQL / MySQL / SQLite / SQL Server (multi-database support)
- Message Queue: Redis (Celery broker)
- Media Integration: Jellyfin API

## Common Commands

### Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Database migration
alembic upgrade head

# Start FastAPI server (dev mode with auto-reload)
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.workers.celery_app worker -l INFO

# Start Celery beat scheduler
celery -A app.workers.celery_app beat -l INFO

# Run tests
pytest -m unit                              # Unit tests only
pytest -m "integration and not slow"        # Integration tests
```

### Frontend Development

```bash
# Install dependencies
pnpm i

# Start dev server
pnpm dev

# Build for production
pnpm build
```

### Docker Compose

```bash
# Start all services
docker compose -f docker-compose.yml up -d

# Environment setup
cp .env.example .env
# Edit .env with required values (JELLYFIN_API_KEY, OLLAMA_BASE_URL, etc.)
```

## Architecture Overview

### Backend Process Topology

The backend consists of multiple independent processes:

1. **FastAPI API Server**: Handles REST endpoints and SSE (Server-Sent Events) for real-time progress updates
2. **Celery Workers**: Execute three types of tasks in separate queues:
   - `scan`: Scan Jellyfin libraries for missing subtitle languages
   - `translate`: Translate existing subtitle files
   - `asr_then_translate`: Extract audio → ASR → translate for media without subtitles
3. **Celery Beat**: Scheduled tasks (periodic scans, cleanup)
4. **Redis**: Celery broker and cache; also used for SSE event forwarding from workers
5. **Database**: SQLAlchemy 2 with synchronous engine (multi-database support)
6. **Ollama**: Separate service for LLM model management and inference
7. **Jellyfin**: External media server integration

### Backend Directory Structure

```
backend/
  app/
    main.py                          # FastAPI application entry
    core/                            # config, db, logging, events
    api/routers/                     # health, models, jellyfin, jobs, upload
    services/                        # business logic layer
      jellyfin_client.py             # Jellyfin API integration
      ollama_client.py               # Ollama API (pull/generate)
      subtitle_service.py            # Subtitle parsing/translation
      asr_service.py                 # faster-whisper integration
      writeback.py                   # Upload to Jellyfin or sidecar
      detector.py                    # Missing language detection
      prompts.py                     # LLM prompt templates
    models/                          # SQLAlchemy ORM models
      types.py                       # Custom types (GUID)
      translation_job.py
      media_asset.py
      subtitle.py
      model_registry.py
      setting.py
      base.py
    schemas/                         # Pydantic request/response schemas
    workers/
      celery_app.py                 # Celery configuration
      tasks.py                      # Task definitions
  migrations/                       # Alembic database migrations
```

### Frontend Architecture

- **State Management**: TanStack Query for server state, Zustand for UI state
- **Real-time Updates**: EventSource (SSE) for task progress streaming
- **Forms**: react-hook-form + zod validation
- **Routing**: Main pages: Dashboard, Models, Library, Jobs, Translate, Settings
- **Styling**: Tailwind CSS with dark mode support, Radix UI for accessible components

### Multi-Database Strategy

The system supports PostgreSQL, MySQL, SQLite, and SQL Server using a unified approach:

- **Primary Keys**: GUID stored as `CHAR(36)` via TypeDecorator for cross-database compatibility
- **Enums**: Stored as `String` with Pydantic validation (avoiding database-specific enum types)
- **Collections**: Media languages use child tables; job target languages use JSON columns
- **Timestamps**: Always stored in UTC with `DateTime(timezone=True)`
- **Migrations**: Alembic scripts avoid dialect-specific features
- **Idempotency**: Service layer uses "check-then-write" instead of dialect-specific UPSERT

### Data Models

**Key Tables:**
- `translation_jobs`: Job status, source/target languages, progress, error logs
- `media_assets`: Jellyfin item metadata, duration, checksums
- `media_audio_langs` / `media_subtitle_langs`: Language availability (child tables for queryability)
- `subtitles`: Subtitle file registry with storage location, format, origin (asr/mt/manual)

**Indexes**: Critical indexes on `(status, created_at)` for job queries, `asset_id` and `lang` for language lookups

## Processing Pipeline

### Translation Pipeline Stages

1. **Model Preparation**: Check Ollama model availability; auto-pull if missing via `/api/pull`
2. **Input Detection**:
   - Existing subtitle → direct translation
   - No subtitle → ASR first
3. **ASR** (optional): FFmpeg audio extraction → faster-whisper → SRT/VTT output
4. **Translation (MT)**:
   - Parse subtitle file with pysubs2
   - Strip ASS formatting tags (e.g., `{\i1}`)
   - Translate plain text via Ollama `/api/generate`
   - Restore formatting tags to translated text
5. **Post-processing**: Punctuation normalization, line length control, tag restoration
6. **Writeback**: Upload to Jellyfin via API or write sidecar file
7. **Registration**: Update `subtitles` table and refresh `media_subtitle_langs`

### ASR Details (faster-whisper)

- Input: 16kHz mono WAV (FFmpeg extraction)
- Long audio: segmented with overlap
- Output: SRT/VTT with timestamps
- Performance: Supports 8-bit quantization, GPU/CPU adaptive

### Translation Details (Ollama)

- **Model Pull**: `/api/pull` with streaming progress (status/completed/total) forwarded to SSE
- **Inference**: `/api/generate` (or `/api/chat`)
- **Prompt Strategy**:
  - System: Professional subtitle translator; no additions/omissions
  - User: Source language, target language, plain text input
  - Output: Translation only (no timestamps/numbering)
- **Batch Processing**: Can merge N lines for token efficiency and context consistency

### Subtitle Format Handling

- **Library**: pysubs2 for reading/writing `.srt/.ass/.vtt`
- **ASS Tags**: Preserve formatting like `{\i1}`, positioning, outline styles
- **Processing Strategy**:
  1. Parse → strip tags → extract plain text
  2. Translate plain text
  3. Restore tags to translated text
  4. Reflow line width/breaks per target language rules

## Critical Technical Details

### FastAPI + Synchronous SQLAlchemy

- Web layer is async, but DB operations use **synchronous SQLAlchemy**
- DB calls wrapped with `run_in_threadpool` for compatibility
- Supports multiple database drivers without async complications

### Celery Configuration

- Key settings: `acks_late`, `task_reject_on_worker_lost`, `worker_max_tasks_per_child`
- Prevents task loss and memory bloat
- Worker concurrency tuned for GPU/CPU resource contention

### SSE Progress Streaming

- Workers publish events to Redis
- API server subscribes and forwards to frontend via EventSource
- Event format: `{ phase, status, completed, total }`
- Phases: `pull → asr → mt → post → writeback`

### JellyfinClient Integration

- `GET /Items?Fields=MediaStreams`: Fetch subtitle/audio language info
- `POST /Items/{itemId}/Subtitles`: Upload subtitle with Data/Format/Language
- Sidecar mode: Write to same directory as media file (optional)

### Database Session Management

```python
# app/core/db.py pattern
engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()
```

## Configuration & Environment

### Required Environment Variables

```ini
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/ai_subs
DB_VENDOR=postgres  # or mysql, sqlite, mssql
REDIS_URL=redis://redis:6379/0
JELLYFIN_BASE_URL=http://jellyfin:8096
JELLYFIN_API_KEY=xxxx
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_KEEP_ALIVE=30m
DEFAULT_MT_MODEL=qwen2.5:7b-instruct
ASR_MODEL=medium
REQUIRED_LANGS=zh-CN,en,ja
WRITEBACK_MODE=upload  # or sidecar
```

### Key Conventions

- **Timezone**: All timestamps stored in UTC
- **Language Codes**: BCP-47 format (validated by Pydantic)
- **Terminology/Glossary**: Optional JSON config; applied before/after translation
- **Format Detection**: Auto-detect subtitle format from file extension

## Code Style & Contributing

### Python (Backend)

- Formatter: ruff + black
- Type checking: mypy for critical modules
- Commit format: Conventional Commits (`feat:`, `fix:`, `docs:`)

### TypeScript (Frontend)

- Linter: eslint
- Formatter: prettier
- Commit format: Conventional Commits

### Pull Requests

- Link related issue
- Include change description and risk assessment
- API changes: Update `docs/03-API_CONTRACT.md`
- Database changes: Include Alembic migration script and rollback assessment

## Testing Strategy

### Test Pyramid

- **Unit**: Subtitle parsing/saving, prompt generation, OllamaClient streaming, DB CRUD
- **Integration**: Ollama + Jellyfin + Redis + DB integration
- **E2E**: Frontend task creation → SSE progress → writeback verification

### Multi-Database CI Matrix

Test against PostgreSQL, MySQL, SQLite, SQL Server:
- Migration success (`alembic upgrade head`)
- CRUD and pagination consistency
- Missing language detection query correctness

### Typical Test Cases

1. Manual SRT upload → translate → preview → upload to Jellyfin
2. Media without subtitle → ASR → translate → upload
3. Missing model → auto `/api/pull` → translate → success
4. Sidecar writeback → Jellyfin auto-detection
5. Long audio → correct segmentation → continuous timeline

## Performance Optimization

### Backend

- Worker concurrency and `prefetch_multiplier` tuning (avoid GPU/ASR contention)
- Large file segmentation for ASR; batch translation with controlled memory
- Jellyfin retry logic with rate limiting
- Ollama `/api/pull` heartbeat detection

### Frontend

- Route-level code splitting
- TanStack Query smart caching and background refresh
- List virtualization (media library, job queue)
- Memo/selector to avoid large object re-renders

## Deployment Notes

- **Processes**: api (Uvicorn), worker (Celery multi-replica), beat (single instance), ollama (separate container)
- **Monitoring**: Structured JSON logs with `job_id, phase, duration, media_id, model`
- **Metrics**: Task throughput/latency/failure rate, model pull time, ASR/MT phase distribution
- **Security**: Minimal Jellyfin API key permissions; internal network in production; optional JWT/Key auth for API
- **Rollback**: Container images with tags; Alembic `downgrade` (use cautiously)

## Documentation Structure

- `docs/00-README.md`: Project overview and quick start
- `docs/01-BACKEND.md`: Backend architecture and development
- `docs/02-FRONTEND.md`: Frontend architecture and development
- `docs/03-API_CONTRACT.md`: OpenAPI endpoint summary
- `docs/04-DATA_MODEL_AND_DB.md`: Database schema and multi-DB strategy
- `docs/05-PIPELINES_ASR_MT_SUBTITLES.md`: AI pipeline details
- `docs/06-DEPLOYMENT_DEVOPS.md`: Deployment and operations
- `docs/07-TESTING_QA.md`: Testing strategy and quality assurance
- `docs/08-CONTRIBUTING.md`: Collaboration and code standards
