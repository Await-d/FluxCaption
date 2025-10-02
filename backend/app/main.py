"""
FluxCaption FastAPI Application.

Main application entry point with route registration and lifecycle management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import init_db, close_db
from app.core.logging import get_logger
from app.api.routers import health, models, upload, jobs, jellyfin, cache
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
