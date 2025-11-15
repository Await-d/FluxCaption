"""
Pydantic schemas for AI model configuration.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AIModelConfigBase(BaseModel):
    """Base schema for AI model configuration."""

    provider_name: str = Field(..., description="Provider name (e.g., 'openai', 'deepseek')")
    model_name: str = Field(
        ..., description="Model identifier (e.g., 'gpt-4', 'qwen2.5:7b-instruct')"
    )
    display_name: str = Field(..., description="Display name for UI")
    is_enabled: bool = Field(default=True, description="Whether this model is enabled")
    model_type: str | None = Field(None, description="Model type (chat, completion, etc.)")
    context_window: int | None = Field(None, ge=0, description="Context window size in tokens")
    max_output_tokens: int | None = Field(None, ge=0, description="Maximum output tokens")
    input_price: float | None = Field(
        None, ge=0, description="Input token price per 1M tokens (USD)"
    )
    output_price: float | None = Field(
        None, ge=0, description="Output token price per 1M tokens (USD)"
    )
    pricing_notes: str | None = Field(None, description="Additional pricing information")
    description: str | None = Field(None, description="Model description")
    tags: str | None = Field(None, description="JSON array of tags")
    is_default: bool = Field(
        default=False, description="Is this the default model for the provider"
    )
    priority: int = Field(default=0, description="Display priority/order")

    @field_validator("display_name", "provider_name", "model_name")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string fields are not empty."""
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v


class AIModelConfigCreate(AIModelConfigBase):
    """Schema for creating a new AI model configuration."""

    pass


class AIModelConfigUpdate(BaseModel):
    """Schema for updating an AI model configuration."""

    display_name: str | None = None
    is_enabled: bool | None = None
    model_type: str | None = None
    context_window: int | None = Field(None, ge=0)
    max_output_tokens: int | None = Field(None, ge=0)
    input_price: float | None = Field(None, ge=0)
    output_price: float | None = Field(None, ge=0)
    pricing_notes: str | None = None
    description: str | None = None
    tags: str | None = None
    is_default: bool | None = None
    priority: int | None = None

    @field_validator("display_name")
    @classmethod
    def validate_non_empty_string(cls, v: str | None) -> str | None:
        """Validate that string fields are not empty."""
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v


class AIModelConfigResponse(AIModelConfigBase):
    """Schema for AI model configuration response."""

    id: str
    is_available: bool
    usage_count: int
    total_input_tokens: int
    total_output_tokens: int
    last_checked: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIModelConfigList(BaseModel):
    """Schema for listing AI model configurations."""

    models: list[AIModelConfigResponse]
    total: int
    page: int = 1
    page_size: int = 50


class PricingCalculation(BaseModel):
    """Schema for pricing calculation response."""

    model_name: str
    provider_name: str
    input_tokens: int
    output_tokens: int
    input_cost: float = Field(description="Cost for input tokens (USD)")
    output_cost: float = Field(description="Cost for output tokens (USD)")
    total_cost: float = Field(description="Total cost (USD)")
    currency: str = Field(default="USD")
