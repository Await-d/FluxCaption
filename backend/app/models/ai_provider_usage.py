"""
AI Provider Usage Log Model.

Tracks API usage and costs for all AI providers.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Float, Integer, Text, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AIProviderUsageLog(BaseModel):
    """
    AI Provider usage and cost tracking.

    Records every API call to cloud AI providers for cost monitoring and analytics.
    """

    __tablename__ = "ai_provider_usage_logs"

    # Provider name (reference to ai_provider_configs)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Model used
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Job/Task reference (if applicable)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Request details
    request_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="generate, list_models, pull_model, etc."
    )

    # Token usage
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Cost calculation
    input_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Cost in USD")
    output_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Cost in USD")
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Total cost in USD")

    # Request metadata
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Response metadata
    finish_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Response time in milliseconds")

    # Error tracking
    is_error: Mapped[bool] = mapped_column(default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User tracking (optional)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Prompt preview (for debugging, truncated)
    prompt_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="First 200 chars of prompt")

    # Response preview (for debugging, truncated)
    response_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="First 200 chars of response")

    # Indexes
    __table_args__ = (
        Index("idx_usage_provider_created", "provider_name", "created_at"),
        Index("idx_usage_date", "created_at"),
        Index("idx_usage_cost", "total_cost"),
        Index("idx_usage_job", "job_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AIProviderUsageLog(provider={self.provider_name}, "
            f"model={self.model_name}, cost=${self.total_cost:.6f})>"
        )


class AIProviderQuota(BaseModel):
    """
    AI Provider quota and budget limits.

    Defines spending limits for each provider to prevent unexpected costs.
    """

    __tablename__ = "ai_provider_quotas"

    # Provider name (reference to ai_provider_configs)
    provider_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Quota limits (in USD)
    daily_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Daily spending limit in USD")
    monthly_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Monthly spending limit in USD")

    # Token limits
    daily_token_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Daily token limit")
    monthly_token_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Monthly token limit")

    # Request rate limits
    requests_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requests_per_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Current usage (cached for performance)
    current_daily_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_monthly_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_daily_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_monthly_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Last reset timestamps
    daily_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    monthly_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Alert settings
    alert_threshold_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=80,
        comment="Alert when usage reaches this % of limit"
    )

    # Whether to automatically disable provider when limit reached
    auto_disable_on_limit: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Last alert sent
    last_alert_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AIProviderQuota(provider={self.provider_name}, "
            f"daily=${self.current_daily_cost:.2f}/{self.daily_limit or 'unlimited'})>"
        )

    def is_daily_limit_exceeded(self) -> bool:
        """Check if daily limit is exceeded."""
        if self.daily_limit is None:
            return False
        return self.current_daily_cost >= self.daily_limit

    def is_monthly_limit_exceeded(self) -> bool:
        """Check if monthly limit is exceeded."""
        if self.monthly_limit is None:
            return False
        return self.current_monthly_cost >= self.monthly_limit

    def is_limit_exceeded(self) -> bool:
        """Check if any limit is exceeded."""
        return self.is_daily_limit_exceeded() or self.is_monthly_limit_exceeded()

    def get_daily_remaining(self) -> Optional[float]:
        """Get remaining daily budget."""
        if self.daily_limit is None:
            return None
        return max(0.0, self.daily_limit - self.current_daily_cost)

    def get_monthly_remaining(self) -> Optional[float]:
        """Get remaining monthly budget."""
        if self.monthly_limit is None:
            return None
        return max(0.0, self.monthly_limit - self.current_monthly_cost)

    def get_usage_percent(self, period: str = "daily") -> float:
        """Get usage as percentage of limit."""
        if period == "daily":
            if self.daily_limit is None or self.daily_limit == 0:
                return 0.0
            return (self.current_daily_cost / self.daily_limit) * 100
        else:  # monthly
            if self.monthly_limit is None or self.monthly_limit == 0:
                return 0.0
            return (self.current_monthly_cost / self.monthly_limit) * 100

    def should_send_alert(self) -> bool:
        """Check if alert should be sent based on threshold."""
        daily_percent = self.get_usage_percent("daily")
        monthly_percent = self.get_usage_percent("monthly")

        return (
            daily_percent >= self.alert_threshold_percent or
            monthly_percent >= self.alert_threshold_percent
        )
