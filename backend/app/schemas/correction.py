"""
Pydantic schemas for correction rules.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CorrectionRuleBase(BaseModel):
    """Base correction rule schema."""

    name: str = Field(..., min_length=1, max_length=255)
    source_pattern: str = Field(..., min_length=1)
    target_text: str = Field(..., min_length=0)
    is_regex: bool = Field(default=False)
    is_case_sensitive: bool = Field(default=True)
    is_active: bool = Field(default=True)
    source_lang: str | None = Field(default=None, max_length=10)
    target_lang: str | None = Field(default=None, max_length=10)
    priority: int = Field(default=0, ge=0, le=100)
    description: str | None = Field(default=None)


class CorrectionRuleCreate(CorrectionRuleBase):
    """Schema for creating a correction rule."""

    pass


class CorrectionRuleUpdate(BaseModel):
    """Schema for updating a correction rule."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    source_pattern: str | None = Field(default=None, min_length=1)
    target_text: str | None = Field(default=None, min_length=0)
    is_regex: bool | None = Field(default=None)
    is_case_sensitive: bool | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    source_lang: str | None = Field(default=None, max_length=10)
    target_lang: str | None = Field(default=None, max_length=10)
    priority: int | None = Field(default=None, ge=0, le=100)
    description: str | None = Field(default=None)


class CorrectionRuleResponse(CorrectionRuleBase):
    """Schema for correction rule response."""

    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CorrectionRuleListResponse(BaseModel):
    """Schema for paginated correction rule list."""

    rules: list[CorrectionRuleResponse]
    total: int
    page: int
    page_size: int


class ApplyCorrectionRequest(BaseModel):
    """Schema for applying correction rules to text."""

    text: str = Field(..., min_length=1)
    source_lang: str | None = Field(default=None)
    target_lang: str | None = Field(default=None)


class ApplyCorrectionResponse(BaseModel):
    """Schema for correction application result."""

    original_text: str
    corrected_text: str
    rules_applied: list[str]  # List of rule IDs applied
