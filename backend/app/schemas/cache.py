"""
Pydantic schemas for translation cache management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CacheEntryResponse(BaseModel):
    """Single cache entry response."""
    
    content_hash: str = Field(..., description="SHA256 hash of the cache key")
    source_text: str = Field(..., description="Source text")
    translated_text: str = Field(..., description="Translated text")
    source_lang: str = Field(..., description="Source language code")
    target_lang: str = Field(..., description="Target language code")
    model: str = Field(..., description="Translation model used")
    hit_count: int = Field(..., description="Number of cache hits")
    created_at: str = Field(..., description="When the entry was created")
    last_used_at: str = Field(..., description="When the entry was last accessed")


class CacheListResponse(BaseModel):
    """Paginated list of cache entries."""
    
    entries: List[CacheEntryResponse] = Field(..., description="List of cache entries")
    total: int = Field(..., description="Total number of entries matching filters")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Number of entries skipped")
    has_more: bool = Field(..., description="Whether there are more entries")


class CacheStatsResponse(BaseModel):
    """Cache statistics."""
    
    total_entries: int = Field(..., description="Total number of cache entries")
    total_hits: int = Field(..., description="Total cache hits across all entries")
    hit_rate: float = Field(..., description="Cache hit rate percentage")
    unique_language_pairs: int = Field(..., description="Number of unique language pairs")
    unique_models: int = Field(..., description="Number of unique models")


class ClearOldEntriesRequest(BaseModel):
    """Request to clear old unused cache entries."""
    
    days: int = Field(default=90, ge=1, le=365, description="Keep entries used within this many days")


class ClearAllEntriesRequest(BaseModel):
    """Request to clear all cache entries."""
    
    confirm: bool = Field(..., description="Must be true to confirm deletion")


class ClearEntriesResponse(BaseModel):
    """Response after clearing cache entries."""
    
    deleted_count: int = Field(..., description="Number of entries deleted")
    message: str = Field(..., description="Success message")
