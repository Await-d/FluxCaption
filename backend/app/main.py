"""
FluxCaption FastAPI Application.

Main application entry point with route registration and lifecycle management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import init_db, close_db, get_db
from app.core.logging import get_logger
from app.core.init_db import init_database
from app.api.routers import health, models, upload, jobs, jellyfin, cache, local_media, subtitles, translation_memory, auth, corrections, auto_translation_rules, system
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
    try:
        init_db()
        logger.info("Database connection established")

        # Initialize database with default data (admin user, etc.)
        with next(get_db()) as db:
            init_database(db)

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
            # Don't fail startup if setting sync fails

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

# Correction rules endpoints
app.include_router(corrections.router)

# Auto translation rules endpoints
app.include_router(auto_translation_rules.router)

# System management endpoints
app.include_router(system.router)

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

# Translation memory endpoints
app.include_router(translation_memory.router)

# Settings management endpoints
app.include_router(settings_router.router)

# Cache management endpoints
app.include_router(cache.router)


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.

    Returns basic API information.
    """
    return {
        "name": "FluxCaption API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs" if settings.enable_swagger_ui else None,
    }


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
