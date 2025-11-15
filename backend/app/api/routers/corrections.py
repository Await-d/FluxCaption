"""
Correction Rules API endpoints.
"""

import logging
import re
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_user
from app.core.db import get_db
from app.models.correction_rule import CorrectionRule
from app.models.user import User
from app.schemas.correction import (
    ApplyCorrectionRequest,
    ApplyCorrectionResponse,
    CorrectionRuleCreate,
    CorrectionRuleListResponse,
    CorrectionRuleResponse,
    CorrectionRuleUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/corrections", tags=["Corrections"])


@router.get("", response_model=CorrectionRuleListResponse)
def list_correction_rules(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active: bool | None = Query(None),
    source_lang: str | None = Query(None),
    target_lang: str | None = Query(None),
):
    """
    List correction rules with optional filtering.

    Args:
        db: Database session
        current_user: Authenticated user
        page: Page number (1-indexed)
        page_size: Number of items per page
        is_active: Filter by active status
        source_lang: Filter by source language
        target_lang: Filter by target language

    Returns:
        CorrectionRuleListResponse: Paginated list of correction rules
    """
    # Build query
    stmt = sa.select(CorrectionRule)

    # Apply filters
    if is_active is not None:
        stmt = stmt.where(CorrectionRule.is_active == is_active)
    if source_lang:
        stmt = stmt.where(
            sa.or_(CorrectionRule.source_lang == source_lang, CorrectionRule.source_lang.is_(None))
        )
    if target_lang:
        stmt = stmt.where(
            sa.or_(CorrectionRule.target_lang == target_lang, CorrectionRule.target_lang.is_(None))
        )

    # Order by priority (descending) then created_at
    stmt = stmt.order_by(CorrectionRule.priority.desc(), CorrectionRule.created_at.desc())

    # Count total
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # Execute query
    rules = list(db.scalars(stmt).all())

    return CorrectionRuleListResponse(
        rules=[CorrectionRuleResponse.model_validate(r) for r in rules],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{rule_id}", response_model=CorrectionRuleResponse)
def get_correction_rule(
    rule_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get a single correction rule by ID.

    Args:
        rule_id: Rule ID
        db: Database session
        current_user: Authenticated user

    Returns:
        CorrectionRuleResponse: Correction rule details

    Raises:
        HTTPException: If rule not found
    """
    stmt = sa.select(CorrectionRule).where(CorrectionRule.id == rule_id)
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(status_code=404, detail="Correction rule not found")

    return CorrectionRuleResponse.model_validate(rule)


@router.post("", response_model=CorrectionRuleResponse, status_code=201)
def create_correction_rule(
    request: CorrectionRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a new correction rule.

    Args:
        request: Rule creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        CorrectionRuleResponse: Created rule

    Raises:
        HTTPException: If regex is invalid
    """
    # Validate regex pattern if is_regex is True
    if request.is_regex:
        try:
            re.compile(request.source_pattern)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Create rule
    rule = CorrectionRule(
        name=request.name,
        source_pattern=request.source_pattern,
        target_text=request.target_text,
        is_regex=request.is_regex,
        is_case_sensitive=request.is_case_sensitive,
        is_active=request.is_active,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        priority=request.priority,
        description=request.description,
        created_by=current_user.username,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    logger.info(f"User {current_user.username} created correction rule {rule.id}: {rule.name}")

    return CorrectionRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=CorrectionRuleResponse)
def update_correction_rule(
    rule_id: str,
    request: CorrectionRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Update an existing correction rule.

    Args:
        rule_id: Rule ID
        request: Update data
        db: Database session
        current_user: Authenticated user

    Returns:
        CorrectionRuleResponse: Updated rule

    Raises:
        HTTPException: If rule not found or regex is invalid
    """
    # Get existing rule
    stmt = sa.select(CorrectionRule).where(CorrectionRule.id == rule_id)
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(status_code=404, detail="Correction rule not found")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    # Validate regex if pattern or is_regex changed
    if "source_pattern" in update_data or "is_regex" in update_data:
        pattern = update_data.get("source_pattern", rule.source_pattern)
        is_regex = update_data.get("is_regex", rule.is_regex)
        if is_regex:
            try:
                re.compile(pattern)
            except re.error as e:
                raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)

    logger.info(f"User {current_user.username} updated correction rule {rule.id}")

    return CorrectionRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_correction_rule(
    rule_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Delete a correction rule.

    Args:
        rule_id: Rule ID
        db: Database session
        current_user: Authenticated user

    Raises:
        HTTPException: If rule not found
    """
    stmt = sa.select(CorrectionRule).where(CorrectionRule.id == rule_id)
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(status_code=404, detail="Correction rule not found")

    db.delete(rule)
    db.commit()

    logger.info(f"User {current_user.username} deleted correction rule {rule_id}")


@router.post("/apply", response_model=ApplyCorrectionResponse)
def apply_corrections(
    request: ApplyCorrectionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Apply correction rules to text.

    Args:
        request: Text and language filters
        db: Database session
        current_user: Authenticated user

    Returns:
        ApplyCorrectionResponse: Original and corrected text with applied rules
    """
    # Get applicable rules
    stmt = sa.select(CorrectionRule).where(CorrectionRule.is_active)

    # Filter by language
    if request.source_lang:
        stmt = stmt.where(
            sa.or_(
                CorrectionRule.source_lang == request.source_lang,
                CorrectionRule.source_lang.is_(None),
            )
        )
    if request.target_lang:
        stmt = stmt.where(
            sa.or_(
                CorrectionRule.target_lang == request.target_lang,
                CorrectionRule.target_lang.is_(None),
            )
        )

    # Order by priority
    stmt = stmt.order_by(CorrectionRule.priority.desc(), CorrectionRule.created_at.asc())

    rules = list(db.scalars(stmt).all())

    # Apply rules
    corrected_text = request.text
    applied_rule_ids = []

    for rule in rules:
        try:
            if rule.is_regex:
                # Use regex replacement
                flags = 0 if rule.is_case_sensitive else re.IGNORECASE
                pattern = re.compile(rule.source_pattern, flags)
                new_text = pattern.sub(rule.target_text, corrected_text)
            else:
                # Use simple string replacement
                if rule.is_case_sensitive:
                    new_text = corrected_text.replace(rule.source_pattern, rule.target_text)
                else:
                    # Case-insensitive replacement
                    pattern = re.compile(re.escape(rule.source_pattern), re.IGNORECASE)
                    new_text = pattern.sub(rule.target_text, corrected_text)

            # Track if rule was applied
            if new_text != corrected_text:
                corrected_text = new_text
                applied_rule_ids.append(rule.id)

        except Exception as e:
            logger.warning(f"Failed to apply correction rule {rule.id}: {e}")
            continue

    logger.info(
        f"Applied {len(applied_rule_ids)} correction rules to text "
        f"(source_lang={request.source_lang}, target_lang={request.target_lang})"
    )

    return ApplyCorrectionResponse(
        original_text=request.text,
        corrected_text=corrected_text,
        rules_applied=applied_rule_ids,
    )
