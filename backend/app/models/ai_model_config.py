"""
AI Model Configuration Model.

Stores model configurations, pricing, and metadata for each AI provider.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, Boolean, Index, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AIModelConfig(BaseModel):
    """
    AI Model configuration and pricing.

    Stores available models for each provider with their pricing information.
    """

    __tablename__ = "ai_model_configs"

    # Provider name (foreign key reference)
    provider_name: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("ai_provider_configs.provider_name", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Model identifier (e.g., "gpt-4", "qwen2.5:7b-instruct")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Display name for UI
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Whether this model is enabled
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Model capabilities/category (e.g., "chat", "completion", "translation")
    model_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Context window size (max tokens)
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Max output tokens
    max_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Pricing information (per 1M tokens)
    # Input token price (USD per 1M tokens)
    input_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Output token price (USD per 1M tokens)
    output_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Additional pricing notes (e.g., "cached tokens: $0.5/1M")
    pricing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model tags (JSON array string, e.g., '["fast", "cheap", "multilingual"]')
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Is this the default model for this provider?
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Display priority/order
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Last time model availability was checked
    last_checked: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Whether model is currently available
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship to provider
    # provider: Mapped["AIProviderConfig"] = relationship(back_populates="models")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_model_provider_name", "provider_name", "model_name"),
        Index("idx_model_enabled", "is_enabled"),
        Index("idx_model_default", "provider_name", "is_default"),
        Index("idx_model_priority", "provider_name", "priority"),
        # Unique constraint: one provider can't have duplicate model names
        Index("uix_provider_model", "provider_name", "model_name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<AIModelConfig(provider={self.provider_name}, model={self.model_name}, enabled={self.is_enabled})>"

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate the cost for given token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            float: Total cost in USD
        """
        if self.input_price is None or self.output_price is None:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * self.input_price
        output_cost = (output_tokens / 1_000_000) * self.output_price

        return input_cost + output_cost

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "is_enabled": self.is_enabled,
            "model_type": self.model_type,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "input_price": self.input_price,
            "output_price": self.output_price,
            "pricing_notes": self.pricing_notes,
            "description": self.description,
            "tags": self.tags,
            "is_default": self.is_default,
            "priority": self.priority,
            "is_available": self.is_available,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
