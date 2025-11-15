"""
Translation Memory API Router.

Provides endpoints for querying translation memory (sentence-level translation pairs).
"""

from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
import re
from datetime import datetime, timezone

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


class UpdateTranslationRequest(BaseModel):
    target_text: str


class BatchDeleteRequest(BaseModel):
    ids: list[str]


class BatchReplaceRequest(BaseModel):
    ids: list[str]
    find: str
    replace: str
    use_regex: bool = False
    case_sensitive: bool = True


class BatchReplaceResponse(BaseModel):
    updated: int
    total: int


class ReProofreadResponse(BaseModel):
    original_text: str
    proofread_text: str
    changed: bool


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


@router.put("/{pair_id}", response_model=TranslationPairResponse)
async def update_translation_pair(
    pair_id: str,
    request: UpdateTranslationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Update a translation pair's target text."""

    tm = db.query(TranslationMemory).filter(TranslationMemory.id == pair_id).first()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation pair not found")

    # Update target text and timestamp
    tm.target_text = request.target_text
    tm.updated_at = datetime.now(timezone.utc)
    tm.word_count_target = len(request.target_text.split())

    db.commit()
    db.refresh(tm)

    # Get media name for response
    media_name = None
    if tm.asset_id:
        asset = db.query(MediaAsset).filter(MediaAsset.id == tm.asset_id).first()
        if asset:
            media_name = asset.name

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


@router.delete("/{pair_id}")
async def delete_translation_pair(
    pair_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Delete a translation pair."""

    tm = db.query(TranslationMemory).filter(TranslationMemory.id == pair_id).first()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation pair not found")

    db.delete(tm)
    db.commit()

    return {"message": "Translation pair deleted successfully", "id": pair_id}


@router.post("/batch-delete")
async def batch_delete_translation_pairs(
    request: BatchDeleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Batch delete translation pairs."""

    # Limit batch size for safety
    if len(request.ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Batch delete limited to 100 items at a time"
        )

    # Delete in transaction
    deleted_count = db.query(TranslationMemory).filter(
        TranslationMemory.id.in_(request.ids)
    ).delete(synchronize_session=False)

    db.commit()

    return {
        "message": f"Deleted {deleted_count} translation pairs",
        "deleted": deleted_count,
        "requested": len(request.ids)
    }


@router.post("/batch-replace", response_model=BatchReplaceResponse)
async def batch_replace_translation_text(
    request: BatchReplaceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Batch find and replace text in translation pairs."""

    # Limit batch size for safety
    if len(request.ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Batch replace limited to 100 items at a time"
        )

    # Validate regex if use_regex is True
    if request.use_regex:
        try:
            re.compile(request.find)
        except re.error as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid regular expression: {str(e)}"
            )

    # Get translation pairs
    pairs = db.query(TranslationMemory).filter(
        TranslationMemory.id.in_(request.ids)
    ).all()

    updated_count = 0

    for pair in pairs:
        original_text = pair.target_text

        if request.use_regex:
            # Regex replacement
            flags = 0 if request.case_sensitive else re.IGNORECASE
            try:
                new_text = re.sub(request.find, request.replace, original_text, flags=flags)
            except re.error:
                continue
        else:
            # Simple string replacement
            if request.case_sensitive:
                new_text = original_text.replace(request.find, request.replace)
            else:
                # Case-insensitive replacement
                pattern = re.compile(re.escape(request.find), re.IGNORECASE)
                new_text = pattern.sub(request.replace, original_text)

        # Only update if text changed
        if new_text != original_text:
            pair.target_text = new_text
            pair.updated_at = datetime.now(timezone.utc)
            pair.word_count_target = len(new_text.split())
            updated_count += 1

    db.commit()

    return BatchReplaceResponse(
        updated=updated_count,
        total=len(request.ids)
    )


@router.post("/{pair_id}/re-proofread", response_model=ReProofreadResponse)
async def re_proofread_translation(
    pair_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Re-proofread a translation using AI."""

    tm = db.query(TranslationMemory).filter(TranslationMemory.id == pair_id).first()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation pair not found")

    # Import AI services
    from app.services.ollama_client import ollama_client
    from app.services.prompts import (
        TRANSLATION_PROOFREADING_SYSTEM_PROMPT,
        build_proofreading_prompt,
    )
    from app.services.subtitle_service import extract_translation_from_response
    from app.core.config import settings

    # Build proofreading prompt
    prompt = build_proofreading_prompt(
        source_lang=tm.source_lang,
        target_lang=tm.target_lang,
        source_text=tm.source_text,
        translated_text=tm.target_text,
    )

    # Call AI for proofreading
    proofread_result = await ollama_client.generate(
        model=settings.default_mt_model,
        prompt=prompt,
        system=TRANSLATION_PROOFREADING_SYSTEM_PROMPT,
        temperature=0.2,
    )

    # Extract translation from response
    proofread_text = extract_translation_from_response(proofread_result)

    # Check if translation changed
    changed = proofread_text != tm.target_text

    return ReProofreadResponse(
        original_text=tm.target_text,
        proofread_text=proofread_text,
        changed=changed,
    )
