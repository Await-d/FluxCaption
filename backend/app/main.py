"""
FluxCaption FastAPI Application.

Main application entry point with route registration and lifecycle management.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import init_db, close_db, get_db
from app.core.logging import get_logger
from app.core.init_db import init_database
from app.api.routers import health, models, upload, jobs, jellyfin, cache, local_media, subtitles, translation_memory, auth, corrections, auto_translation_rules, system, subtitle_sync, ai_providers, ai_models, system_config
from app.api.routers import settings as settings_router

logger = get_logger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting FluxCaption application...")

    # Run database migrations automatically before initializing
    try:
        logger.info("Checking database migration status...")
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from pathlib import Path
        from sqlalchemy import create_engine

        # Get alembic.ini path
        backend_dir = Path(__file__).parent.parent
        alembic_cfg = Config(str(backend_dir / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))

        # Check if migration is needed
        from app.core.config import settings
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()

            script = ScriptDirectory.from_config(alembic_cfg)
            head = script.get_current_head()

            if current != head:
                logger.info(f"Upgrading database: {current} -> {head}")
                command.upgrade(alembic_cfg, "head")
                logger.info("✅ Database migrations completed successfully")
            else:
                logger.info(f"✅ Database already at latest version: {current}")

        engine.dispose()

    except Exception as e:
        logger.warning(f"Database migration check/run failed: {e}", exc_info=True)
        # Continue startup - migrations might have already been run by start.sh

    try:
        init_db()
        logger.info("Database connection established")

        # Initialize database with default data (admin user, etc.)
        with next(get_db()) as db:
            init_database(db)

        # Initialize system settings with default values
        try:
            logger.info("Initializing system settings...")
            with next(get_db()) as db:
                from app.core.init_settings import init_system_settings
                init_system_settings(db)

                # Preload runtime configuration from database
                from app.core.runtime_config import load_config_from_db
                load_config_from_db(db)

            logger.info("System settings initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize system settings: {e}", exc_info=True)
            # Don't fail startup if settings init fails

        # Run database health check and auto-repair
        try:
            logger.info("Running database health check...")
            with next(get_db()) as db:
                from app.core.db_health import check_and_repair_database
                results = check_and_repair_database(db)

                if results['initial_status'] != 'healthy':
                    logger.warning(f"Database health issues detected: {results['initial_status']}")
                    if results['repairs']:
                        logger.info(f"Database repairs made: {results['repairs']}")
                    if results['errors']:
                        logger.error(f"Database repair errors: {results['errors']}")
                    logger.info(f"Final database status: {results['final_status']}")
                else:
                    logger.info("Database health check passed")
        except Exception as e:
            logger.warning(f"Database health check failed: {e}", exc_info=True)
            # Don't fail startup if health check fails

        # Initialize AI providers from environment variables
        try:
            logger.info("Initializing AI provider configurations...")
            with next(get_db()) as db:
                from app.core.init_ai_providers import init_ai_providers
                init_ai_providers(db)
            logger.info("AI provider initialization completed")
        except Exception as e:
            logger.warning(f"Failed to initialize AI providers: {e}", exc_info=True)
            # Don't fail startup if provider init fails

        # Sync models from Ollama to database (must be outside db context)
        try:
            logger.info("Syncing models from Ollama...")
            with next(get_db()) as db:
                from app.core.model_sync import sync_models_from_ollama
                await sync_models_from_ollama(db)
            logger.info("Model sync completed")
        except Exception as e:
            logger.warning(f"Failed to sync models from Ollama: {e}", exc_info=True)
            # Don't fail startup if model sync fails

        # Sync default model from database to runtime settings
        try:
            logger.info("Syncing default model from database...")
            with next(get_db()) as db:
                from app.models.setting import Setting
                default_model_setting = db.query(Setting).filter(
                    Setting.key == "default_mt_model"
                ).first()

                if default_model_setting:
                    # Update the settings object directly (it's a singleton)
                    settings.default_mt_model = default_model_setting.value
                    logger.info(f"Default model synced from database: {default_model_setting.value}")
                    logger.info(f"Verified runtime value: {settings.default_mt_model}")
                else:
                    logger.info(f"No default model in database, using config default: {settings.default_mt_model}")
        except Exception as e:
            logger.warning(f"Failed to sync default model from database: {e}", exc_info=True)

        # Load Jellyfin settings from database
        try:
            logger.info("Loading Jellyfin configuration from database...")
            from app.core.config import load_jellyfin_settings_from_db
            load_jellyfin_settings_from_db()
            logger.info("Jellyfin configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load Jellyfin settings from database: {e}", exc_info=True)
            # Don't fail startup if setting sync fails

        # Reset stuck running jobs after server restart
        try:
            logger.info("Checking for stuck running jobs...")
            with next(get_db()) as db:
                from app.models.translation_job import TranslationJob
                from datetime import datetime, timezone
                
                stuck_jobs = db.query(TranslationJob).filter(
                    TranslationJob.status == "running"
                ).all()
                
                if stuck_jobs:
                    logger.warning(f"Found {len(stuck_jobs)} stuck running jobs, marking as failed...")
                    for job in stuck_jobs:
                        job.status = "failed"
                        job.error = "任务因服务重启而中断 (Task interrupted by server restart)"
                        job.finished_at = datetime.now(timezone.utc)
                        logger.info(f"Reset stuck job: {job.id}")
                    
                    db.commit()
                    logger.info(f"Successfully reset {len(stuck_jobs)} stuck jobs")
                else:
                    logger.info("No stuck running jobs found")
        except Exception as e:
            logger.warning(f"Failed to reset stuck jobs: {e}", exc_info=True)
            # Don't fail startup if job reset fails

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down FluxCaption application...")
    close_db()
    logger.info("Application shutdown complete")


# =============================================================================
# Application Instance
# =============================================================================

app = FastAPI(
    title="FluxCaption API",
    description="AI-powered subtitle translation system for Jellyfin media libraries",
    version="0.1.0",
    docs_url="/docs" if settings.enable_swagger_ui else None,
    redoc_url="/redoc" if settings.enable_swagger_ui else None,
    lifespan=lifespan,
)


# =============================================================================
# CORS Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler.

    Catches all unhandled exceptions and returns a proper error response.
    """
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method},
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
            "message": str(exc) if settings.debug else "An error occurred",
        },
    )


# =============================================================================
# Route Registration
# =============================================================================

# Authentication endpoints
app.include_router(auth.router)

# AI provider management endpoints
app.include_router(ai_providers.router)

# AI model configuration endpoints
app.include_router(ai_models.router)

# Correction rules endpoints
app.include_router(corrections.router)

# Auto translation rules endpoints
app.include_router(auto_translation_rules.router)

# System management endpoints
app.include_router(system.router)

# System configuration endpoints
app.include_router(system_config.router)

# Health check endpoints
app.include_router(health.router)

# Model management endpoints
app.include_router(models.router)

# File upload endpoints
app.include_router(upload.router)

# Job management endpoints
app.include_router(jobs.router)

# Jellyfin integration endpoints
app.include_router(jellyfin.router)

# Local media file endpoints
app.include_router(local_media.router)

# Subtitle library endpoints
app.include_router(subtitles.router)

# Subtitle sync endpoints
app.include_router(subtitle_sync.router)

# Translation memory endpoints
app.include_router(translation_memory.router)

# Settings management endpoints
app.include_router(settings_router.router)

# Cache management endpoints
app.include_router(cache.router)


# =============================================================================
# Static Files and Frontend Routes
# =============================================================================

# Define frontend static files directory
FRONTEND_DIST = Path(__file__).parent.parent / "frontend_dist"

# Mount static files if the directory exists
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
    logger.info(f"Frontend static files mounted from {FRONTEND_DIST}")

    # Add a root route for frontend
    @app.get("/", tags=["Frontend"], include_in_schema=False)
    async def serve_index():
        """Serve frontend index page."""
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse(status_code=404, content={"detail": "Frontend not found"})

    # Custom 404 handler that serves frontend for non-API routes
    @app.exception_handler(404)
    async def custom_404_handler(request, exc):
        """
        Custom 404 handler.

        For API routes (/api/*), returns JSON error.
        For other routes, serves frontend SPA (index.html).
        """
        # Check if it's an API route
        if request.url.path.startswith("/api/") or request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"}
            )

        # For non-API routes, serve frontend SPA
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        return JSONResponse(
            status_code=404,
            content={"detail": "Page not found"}
        )
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIST}")


# =============================================================================
# Root Endpoint (API Mode)
# =============================================================================

# This will only be reached if frontend is not mounted
# @app.get("/", tags=["Root"])
# async def root():
#     """
#     Root endpoint.
#
#     Returns basic API information.
#     """
#     return {
#         "name": "FluxCaption API",
#         "version": "0.1.0",
#         "status": "running",
#         "docs": "/docs" if settings.enable_swagger_ui else None,
#     }


# =============================================================================
# Development Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.auto_reload,
        log_level=settings.log_level.lower(),
    )
