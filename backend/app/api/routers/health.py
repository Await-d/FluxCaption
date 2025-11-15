"""
Health check endpoints.

Provides basic health check and detailed readiness check.
"""

import time
from datetime import UTC

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.db import check_db_health
from app.core.logging import get_logger
from app.schemas.health import ComponentStatus, HealthResponse, ReadyResponse
from app.services.ollama_client import ollama_client

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint matching frontend expectations.

    Returns a health status with individual service statuses.
    This endpoint checks all critical services and returns their status.

    Returns:
        HealthResponse: Detailed health status with service information
    """
    from datetime import datetime

    # Check database
    db_status = "ok" if check_db_health() else "down"

    # Check Ollama
    ollama_status = "ok" if await ollama_client.health_check() else "down"

    # Check Redis (placeholder - always ok for now)
    redis_status = "ok"

    # Check Jellyfin (placeholder - always ok for now)
    jellyfin_status = "ok"

    # Determine overall status
    services = {
        "database": db_status,
        "redis": redis_status,
        "ollama": ollama_status,
        "jellyfin": jellyfin_status,
    }

    # Overall status: ok if all ok, down if any critical service down, degraded if some down
    if all(s == "ok" for s in services.values()):
        overall_status = "ok"
    elif db_status == "down":
        overall_status = "down"
    else:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        services=services,
        version="0.1.0",
    )


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
)
async def readiness_check() -> ReadyResponse:
    """
    Detailed readiness check endpoint.

    Checks the health of all critical components:
    - Database connection
    - Ollama server
    - Redis (future)

    Returns:
        ReadyResponse: Detailed component health status
    """
    components = []
    all_healthy = True

    # Check database
    start_time = time.time()
    db_healthy = check_db_health()
    db_latency = (time.time() - start_time) * 1000

    components.append(
        ComponentStatus(
            name="database",
            status="healthy" if db_healthy else "unhealthy",
            message="Database connection successful"
            if db_healthy
            else "Database connection failed",
            latency_ms=db_latency,
        )
    )

    if not db_healthy:
        all_healthy = False

    # Check Ollama
    start_time = time.time()
    ollama_healthy = await ollama_client.health_check()
    ollama_latency = (time.time() - start_time) * 1000

    components.append(
        ComponentStatus(
            name="ollama",
            status="healthy" if ollama_healthy else "unhealthy",
            message="Ollama server accessible"
            if ollama_healthy
            else "Ollama server not accessible",
            latency_ms=ollama_latency,
        )
    )

    if not ollama_healthy:
        all_healthy = False

    # TODO: Add Redis health check

    response = ReadyResponse(ready=all_healthy, components=components)

    # Return 503 if not ready
    if not all_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(),
        )

    return response
