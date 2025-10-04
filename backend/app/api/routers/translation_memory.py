"""
Translation Memory API Router.

Provides endpoints for querying translation memory (sentence-level translation pairs).
"""

from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc

from app.core.db import get_db
from app.models.user import User
from app.api.routers.auth import get_current_user
from app.models.translation_memory import TranslationMemory
from app.models.media_asset import MediaAsset
from pydantic import BaseModel


router = APIRouter(prefix="/api/translation-memory", tags=["translation-memory"])


# =============================================================================
# Schemas
# =============================================================================

class TranslationPairResponse(BaseModel):
    id: str
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    context: Optional[str] = None
    media_name: Optional[str] = None
    line_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    word_count_source: Optional[int] = None
    word_count_target: Optional[int] = None
    translation_model: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class TranslationMemoryListResponse(BaseModel):
    pairs: list[TranslationPairResponse]
    total: int
    limit: int
    offset: int


class TranslationMemoryStatsResponse(BaseModel):
    total: int
    by_language_pair: dict[str, int]
    by_model: dict[str, int]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=TranslationMemoryListResponse)
async def list_translation_pairs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source_lang: Optional[str] = Query(default=None, description="Filter by source language"),
    target_lang: Optional[str] = Query(default=None, description="Filter by target language"),
    search: Optional[str] = Query(default=None, description="Search in source or target text"),
):
    """List translation memory pairs with pagination and filters."""

    # Build query with joins
    query = db.query(
        TranslationMemory,
        MediaAsset.name.label('media_name'),
    ).outerjoin(
        MediaAsset, TranslationMemory.asset_id == MediaAsset.id
    )

    # Apply filters
    if source_lang:
        query = query.filter(TranslationMemory.source_lang == source_lang)

    if target_lang:
        query = query.filter(TranslationMemory.target_lang == target_lang)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                TranslationMemory.source_text.ilike(search_pattern),
                TranslationMemory.target_text.ilike(search_pattern),
                MediaAsset.name.ilike(search_pattern),
            )
        )

    # Get total count
    total = query.count()

    # Get paginated results (ordered by newest first)
    results = query.order_by(desc(TranslationMemory.created_at)).limit(limit).offset(offset).all()

    # Format response
    pairs = []
    for tm, media_name in results:
        pairs.append(
            TranslationPairResponse(
                id=str(tm.id),
                source_text=tm.source_text,
                target_text=tm.target_text,
                source_lang=tm.source_lang,
                target_lang=tm.target_lang,
                context=tm.context,
                media_name=media_name,
                line_number=tm.line_number,
                start_time=tm.start_time,
                end_time=tm.end_time,
                word_count_source=tm.word_count_source,
                word_count_target=tm.word_count_target,
                translation_model=tm.translation_model,
                created_at=tm.created_at.isoformat(),
            )
        )

    return TranslationMemoryListResponse(
        pairs=pairs,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=TranslationMemoryStatsResponse)
async def get_translation_memory_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Get translation memory statistics."""

    # Total count
    total = db.query(func.count(TranslationMemory.id)).scalar() or 0

    # By language pair
    lang_pair_counts = db.query(
        func.concat(TranslationMemory.source_lang, ' → ', TranslationMemory.target_lang).label('pair'),
        func.count(TranslationMemory.id).label('count')
    ).group_by('pair').all()

    by_language_pair = {pair: count for pair, count in lang_pair_counts}

    # By model
    model_counts = db.query(
        TranslationMemory.translation_model,
        func.count(TranslationMemory.id).label('count')
    ).filter(
        TranslationMemory.translation_model.isnot(None)
    ).group_by(
        TranslationMemory.translation_model
    ).all()

    by_model = {model or 'Unknown': count for model, count in model_counts}

    return TranslationMemoryStatsResponse(
        total=total,
        by_language_pair=by_language_pair,
        by_model=by_model,
    )


@router.get("/{pair_id}", response_model=TranslationPairResponse)
async def get_translation_pair(
    pair_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Get a specific translation pair by ID."""

    result = db.query(
        TranslationMemory,
        MediaAsset.name.label('media_name'),
    ).outerjoin(
        MediaAsset, TranslationMemory.asset_id == MediaAsset.id
    ).filter(
        TranslationMemory.id == pair_id
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Translation pair not found")

    tm, media_name = result

    return TranslationPairResponse(
        id=str(tm.id),
        source_text=tm.source_text,
        target_text=tm.target_text,
        source_lang=tm.source_lang,
        target_lang=tm.target_lang,
        context=tm.context,
        media_name=media_name,
        line_number=tm.line_number,
        start_time=tm.start_time,
        end_time=tm.end_time,
        word_count_source=tm.word_count_source,
        word_count_target=tm.word_count_target,
        translation_model=tm.translation_model,
        created_at=tm.created_at.isoformat(),
    )
