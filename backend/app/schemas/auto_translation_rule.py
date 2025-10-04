"""
Pydantic schemas for auto translation rules.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_serializer, field_validator


class AutoTranslationRuleCreate(BaseModel):
    """Schema for creating an auto translation rule."""
    name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = Field(default=True)
    jellyfin_library_ids: list[str] = Field(default_factory=list)
    source_lang: str | None = Field(default=None)
    target_langs: list[str] = Field(..., min_length=1)
    auto_start: bool = Field(default=True)
    priority: int = Field(default=5, ge=1, le=10)

    @field_validator('target_langs')
    @classmethod
    def validate_target_langs(cls, v):
        if not v or len(v) == 0:
            raise ValueError("target_langs must contain at least one language")
        return v


class AutoTranslationRuleUpdate(BaseModel):
    """Schema for updating an auto translation rule."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    jellyfin_library_ids: list[str] | None = None
    source_lang: str | None = None
    target_langs: list[str] | None = None
    auto_start: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=10)

    @field_validator('target_langs')
    @classmethod
    def validate_target_langs(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("target_langs must contain at least one language")
        return v


class AutoTranslationRuleResponse(BaseModel):
    """Schema for auto translation rule response."""
    id: UUID
    user_id: UUID
    name: str
    enabled: bool
    jellyfin_library_ids: list[str]
    source_lang: str | None
    target_langs: list[str]
    auto_start: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer('id', 'user_id')
    def serialize_uuid(self, uuid_val: UUID, _info):
        return str(uuid_val)


class AutoTranslationRuleListResponse(BaseModel):
    """Schema for list of auto translation rules."""
    rules: list[AutoTranslationRuleResponse]
    total: int
