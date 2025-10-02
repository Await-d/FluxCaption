"""
Health check schemas.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response matching frontend expectations."""

    status: str = Field(description="Overall health status: ok | degraded | down")
    timestamp: str = Field(description="ISO 8601 timestamp")
    services: dict[str, str] = Field(
        description="Individual service statuses: database, redis, ollama, jellyfin"
    )
    version: str = Field(default="0.1.0", description="Application version")


class ComponentStatus(BaseModel):
    """Individual component health status."""

    name: str = Field(description="Component name")
    status: str = Field(description="Component status: healthy | unhealthy | unknown")
    message: str | None = Field(default=None, description="Status message or error")
    latency_ms: float | None = Field(default=None, description="Response latency in milliseconds")


class ReadyResponse(BaseModel):
    """Readiness check response with component status."""

    ready: bool = Field(description="Overall readiness status")
    components: list[ComponentStatus] = Field(description="Individual component statuses")
