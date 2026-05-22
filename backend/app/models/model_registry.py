"""
Model Registry for tracking AI models across all providers.

Tracks model availability, download status, and metadata for all AI providers
(Ollama, OpenAI, DeepSeek, Claude, etc.).
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, BigInteger, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ModelRegistry(BaseModel):
    """
    Registry of AI models tracked by the system.

    Tracks model availability, download status, and metadata across all providers.
    """

    __tablename__ = "model_registry"

    # Provider name (e.g., "ollama", "openai", "deepseek", "claude")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Model name (e.g., "qwen2.5:7b-instruct", "gpt-4", "claude-3-sonnet")
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Model status: available | pulling | failed | deleted
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")

    # Model size in bytes
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Model format (e.g., "gguf")
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Model family (e.g., "qwen2.5", "llama3")
    family: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Parameter count (e.g., "7B", "13B")
    parameter_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Quantization (e.g., "Q4_K_M", "Q8_0")
    quantization: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Last time the model was checked/verified
    last_checked: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        nullable=False,
    )

    # Last time the model was used
    last_used: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Pull progress (JSON: {status, completed, total})
    pull_progress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Error message if status is 'failed'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model digest/hash for verification
    digest: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Usage count
    usage_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Is this the default model for translation?
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Context window size (tokens)
    context_length: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Cost per 1k input tokens (USD)
    cost_input_per_1k: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Cost per 1k output tokens (USD)
    cost_output_per_1k: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Model description
    model_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes and constraints
    __table_args__ = (
        # Unique constraint on (provider, name) combination
        UniqueConstraint("provider", "name", name="uq_provider_model"),
        Index("idx_model_status", "status"),
        Index("idx_model_last_used", "last_used"),
        Index("idx_model_provider_status", "provider", "status"),
    )

    def __repr__(self) -> str:
        return f"<ModelRegistry(provider={self.provider}, name={self.name}, status={self.status})>"

    @property
    def full_model_id(self) -> str:
        """Get the fully qualified model identifier (provider:model)."""
        return f"{self.provider}:{self.name}"
