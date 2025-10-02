"""
Ollama model management schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Information about an Ollama model."""

    name: str = Field(description="Model name")
    status: str = Field(description="Model status: available | pulling | failed")
    size_bytes: int | None = Field(default=None, description="Model size in bytes")
    family: str | None = Field(default=None, description="Model family")
    parameter_size: str | None = Field(default=None, description="Parameter count")
    quantization: str | None = Field(default=None, description="Quantization type")
    last_checked: datetime = Field(description="Last check timestamp")
    last_used: datetime | None = Field(default=None, description="Last usage timestamp")
    usage_count: int = Field(default=0, description="Usage count")
    is_default: bool = Field(default=False, description="Is default model")

    class Config:
        from_attributes = True


class ModelPullRequest(BaseModel):
    """Request to pull an Ollama model."""

    name: str = Field(description="Model name to pull", examples=["qwen2.5:7b-instruct"])
    insecure: bool = Field(default=False, description="Allow insecure connections")


class ModelPullProgress(BaseModel):
    """Progress update during model pull."""

    status: str = Field(description="Status message")
    digest: str | None = Field(default=None, description="Layer digest")
    total: int | None = Field(default=None, description="Total bytes")
    completed: int | None = Field(default=None, description="Completed bytes")


class ModelDeleteResponse(BaseModel):
    """Response after deleting a model."""

    success: bool = Field(description="Whether deletion was successful")
    message: str = Field(description="Status message")


class ModelListResponse(BaseModel):
    """List of models."""

    models: list[ModelInfo] = Field(description="List of models")
    total: int = Field(description="Total number of models")
