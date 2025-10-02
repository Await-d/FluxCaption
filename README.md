# FluxCaption

> AI-Powered Subtitle Translation System for Jellyfin Media Libraries

FluxCaption is a comprehensive subtitle translation system that automatically detects missing subtitle languages in your Jellyfin media library, performs ASR (Automatic Speech Recognition) on media without subtitles, and translates subtitles using local LLM models via Ollama.

## ✨ Features

- 🎯 **Automatic Language Detection** - Scans Jellyfin libraries for missing subtitle languages
- 🎙️ **ASR Support** - Generates subtitles from audio using faster-whisper
- 🌐 **AI Translation** - Translates subtitles using local LLM models (Ollama)
- 📝 **Format Support** - Handles `.srt`, `.ass`, and `.vtt` subtitle formats
- 🗄️ **Multi-Database** - Supports PostgreSQL, MySQL, SQLite, and SQL Server
- 🔄 **Real-time Progress** - SSE-based progress tracking
- 🎨 **Modern UI** - React 19 with Tailwind CSS and Radix UI
- 🚀 **Production-Ready** - Complete error handling, logging, and monitoring

## 🏗️ Architecture

### Tech Stack

**Backend:**
- FastAPI (async web framework)
- Celery (distributed task processing)
- SQLAlchemy 2 (ORM with multi-database support)
- Alembic (database migrations)
- Redis (message broker & cache)
- Ollama (local LLM inference)
- faster-whisper (ASR engine)

**Frontend:**
- React 19
- Vite (build tool)
- TypeScript
- TanStack Query (server state)
- Zustand (UI state)
- Tailwind CSS + Radix UI
- React Hook Form + Zod

**Infrastructure:**
- Docker Compose
- PostgreSQL (default database)
- Redis
- Ollama

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/FluxCaption.git
   cd FluxCaption
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Jellyfin API key and other settings
   ```

3. **Start all services:**
   ```bash
   docker compose up -d
   ```

4. **Run database migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. **Access the application:**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - Frontend: http://localhost:5173 (in development)

## 📖 Documentation

Detailed documentation is available in the `docs/` directory:

- [00-README.md](docs/00-README.md) - Project overview
- [01-BACKEND.md](docs/01-BACKEND.md) - Backend architecture
- [02-FRONTEND.md](docs/02-FRONTEND.md) - Frontend architecture
- [03-API_CONTRACT.md](docs/03-API_CONTRACT.md) - API endpoints
- [04-DATA_MODEL_AND_DB.md](docs/04-DATA_MODEL_AND_DB.md) - Database schema
- [05-PIPELINES_ASR_MT_SUBTITLES.md](docs/05-PIPELINES_ASR_MT_SUBTITLES.md) - Processing pipelines
- [06-DEPLOYMENT_DEVOPS.md](docs/06-DEPLOYMENT_DEVOPS.md) - Deployment guide
- [07-TESTING_QA.md](docs/07-TESTING_QA.md) - Testing strategy
- [08-CONTRIBUTING.md](docs/08-CONTRIBUTING.md) - Contribution guidelines

## 🛠️ Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.workers.celery_app worker -l INFO

# Start Celery beat
celery -A app.workers.celery_app beat -l INFO

# Run tests
pytest
```

### Frontend Development

```bash
cd frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build
```

## 📋 Environment Variables

Key configuration options (see `.env.example` for full list):

```ini
# Database
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/fluxcaption
DB_VENDOR=postgres

# Jellyfin
JELLYFIN_BASE_URL=http://jellyfin:8096
JELLYFIN_API_KEY=your_api_key_here

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
DEFAULT_MT_MODEL=qwen2.5:7b-instruct

# ASR
ASR_MODEL=medium
ASR_DEVICE=auto

# Languages
REQUIRED_LANGS=zh-CN,en,ja
WRITEBACK_MODE=upload
```

## 🎯 Usage

### API Examples

**List Models:**
```bash
curl http://localhost:8000/api/models
```

**Pull a Model:**
```bash
curl -X POST http://localhost:8000/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "qwen2.5:7b-instruct"}'
```

**Create Translation Job:**
```bash
curl -X POST http://localhost:8000/api/jobs/translate \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "subtitle",
    "source_path": "/path/to/subtitle.srt",
    "source_lang": "en",
    "target_langs": ["zh-CN"],
    "model": "qwen2.5:7b-instruct"
  }'
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -m unit                              # Unit tests
pytest -m integration                       # Integration tests
pytest --cov=app tests/                     # With coverage

# Frontend tests
cd frontend
pnpm test
```

## 📊 Project Status

**Current Phase:** ✅ M1 - Foundation Complete

- [x] Project structure
- [x] Docker configuration
- [x] Core backend (config, logging, database)
- [x] Database models (SQLAlchemy + Alembic)
- [x] Ollama client service
- [x] Health & model management APIs
- [x] Celery task framework
- [x] Frontend foundation (React 19 + Vite)
- [ ] M2 - Subtitle translation pipeline
- [ ] M3 - Jellyfin integration
- [ ] M4 - ASR pipeline
- [ ] M5 - Complete UI

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](docs/08-CONTRIBUTING.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local LLM inference
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Fast ASR
- [Jellyfin](https://jellyfin.org/) - Media server
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [React](https://react.dev/) - UI framework

## 📮 Contact

- Issues: [GitHub Issues](https://github.com/yourusername/FluxCaption/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/FluxCaption/discussions)

---

**Made with ❤️ for the Jellyfin community**
