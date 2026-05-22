"""
AI Provider Configuration Model.

Stores provider configurations and credentials in the database.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AIProviderConfig(BaseModel):
    """
    AI Provider configuration and credentials.

    Stores settings for different AI providers (OpenAI, DeepSeek, Claude, etc.).
    """

    __tablename__ = "ai_provider_configs"

    # Provider name (ollama, openai, deepseek, claude, etc.)
    provider_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Display name for UI
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Whether this provider is enabled
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # API key (encrypted in production)
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Base URL for API
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Request timeout in seconds
    timeout: Mapped[int] = mapped_column(default=300, nullable=False)

    # Additional configuration (JSON string)
    # Example: {"organization_id": "org-xxx", "max_retries": 3}
    extra_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Default model to use for this provider
    default_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Last time this provider was checked
    last_health_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Whether last health check passed
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Health check error message (if failed)
    health_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Priority/order for displaying in UI
    priority: Mapped[int] = mapped_column(default=0, nullable=False)

    # Description for UI
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_provider_enabled", "is_enabled"),
        Index("idx_provider_priority", "priority"),
    )

    def __repr__(self) -> str:
        return f"<AIProviderConfig(provider={self.provider_name}, enabled={self.is_enabled})>"
