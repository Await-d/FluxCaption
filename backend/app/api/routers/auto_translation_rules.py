"""
Auto Translation Rules API endpoints.
"""

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sqlalchemy as sa

from app.core.db import get_db
from app.models.auto_translation_rule import AutoTranslationRule
from app.models.user import User
from app.api.routers.auth import get_current_user
from app.schemas.auto_translation_rule import (
    AutoTranslationRuleCreate,
    AutoTranslationRuleUpdate,
    AutoTranslationRuleResponse,
    AutoTranslationRuleListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-translation-rules", tags=["Auto Translation Rules"])


@router.get("", response_model=AutoTranslationRuleListResponse, summary="List auto translation rules")
async def list_rules(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AutoTranslationRuleListResponse:
    """
    Get all auto translation rules for the current user.

    Returns:
        List of auto translation rules
    """
    stmt = (
        sa.select(AutoTranslationRule)
        .where(AutoTranslationRule.user_id == current_user.id)
        .order_by(AutoTranslationRule.created_at.desc())
    )
    rules = db.scalars(stmt).all()

    # Parse JSON fields
    rule_responses = []
    for rule in rules:
        rule_responses.append(
            AutoTranslationRuleResponse(
                id=rule.id,
                user_id=rule.user_id,
                name=rule.name,
                enabled=rule.enabled,
                jellyfin_library_ids=json.loads(rule.jellyfin_library_ids),
                source_lang=rule.source_lang,
                target_langs=json.loads(rule.target_langs),
                auto_start=rule.auto_start,
                priority=rule.priority,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )
        )

    return AutoTranslationRuleListResponse(
        rules=rule_responses,
        total=len(rule_responses),
    )


@router.get("/{rule_id}", response_model=AutoTranslationRuleResponse, summary="Get a specific rule")
async def get_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AutoTranslationRuleResponse:
    """
    Get a specific auto translation rule by ID.

    Args:
        rule_id: Rule UUID

    Returns:
        Auto translation rule details
    """
    stmt = sa.select(AutoTranslationRule).where(
        AutoTranslationRule.id == rule_id,
        AutoTranslationRule.user_id == current_user.id,
    )
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    return AutoTranslationRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        enabled=rule.enabled,
        jellyfin_library_ids=json.loads(rule.jellyfin_library_ids),
        source_lang=rule.source_lang,
        target_langs=json.loads(rule.target_langs),
        auto_start=rule.auto_start,
        priority=rule.priority,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.post("", response_model=AutoTranslationRuleResponse, summary="Create a new rule")
async def create_rule(
    rule_data: AutoTranslationRuleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AutoTranslationRuleResponse:
    """
    Create a new auto translation rule.

    Args:
        rule_data: Rule creation data

    Returns:
        Created rule details
    """
    # Create new rule
    rule = AutoTranslationRule(
        user_id=current_user.id,
        name=rule_data.name,
        enabled=rule_data.enabled,
        jellyfin_library_ids=json.dumps(rule_data.jellyfin_library_ids),
        source_lang=rule_data.source_lang,
        target_langs=json.dumps(rule_data.target_langs),
        auto_start=rule_data.auto_start,
        priority=rule_data.priority,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    logger.info(f"Created auto translation rule {rule.id} for user {current_user.username}")

    return AutoTranslationRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        enabled=rule.enabled,
        jellyfin_library_ids=json.loads(rule.jellyfin_library_ids),
        source_lang=rule.source_lang,
        target_langs=json.loads(rule.target_langs),
        auto_start=rule.auto_start,
        priority=rule.priority,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.put("/{rule_id}", response_model=AutoTranslationRuleResponse, summary="Update a rule")
async def update_rule(
    rule_id: UUID,
    rule_data: AutoTranslationRuleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AutoTranslationRuleResponse:
    """
    Update an existing auto translation rule.

    Args:
        rule_id: Rule UUID
        rule_data: Rule update data

    Returns:
        Updated rule details
    """
    stmt = sa.select(AutoTranslationRule).where(
        AutoTranslationRule.id == rule_id,
        AutoTranslationRule.user_id == current_user.id,
    )
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    # Update fields
    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.enabled is not None:
        rule.enabled = rule_data.enabled
    if rule_data.jellyfin_library_ids is not None:
        rule.jellyfin_library_ids = json.dumps(rule_data.jellyfin_library_ids)
    if rule_data.source_lang is not None:
        rule.source_lang = rule_data.source_lang
    if rule_data.target_langs is not None:
        rule.target_langs = json.dumps(rule_data.target_langs)
    if rule_data.auto_start is not None:
        rule.auto_start = rule_data.auto_start
    if rule_data.priority is not None:
        rule.priority = rule_data.priority

    db.commit()
    db.refresh(rule)

    logger.info(f"Updated auto translation rule {rule.id}")

    return AutoTranslationRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        enabled=rule.enabled,
        jellyfin_library_ids=json.loads(rule.jellyfin_library_ids),
        source_lang=rule.source_lang,
        target_langs=json.loads(rule.target_langs),
        auto_start=rule.auto_start,
        priority=rule.priority,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a rule")
async def delete_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an auto translation rule.

    Args:
        rule_id: Rule UUID
    """
    stmt = sa.select(AutoTranslationRule).where(
        AutoTranslationRule.id == rule_id,
        AutoTranslationRule.user_id == current_user.id,
    )
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    db.delete(rule)
    db.commit()

    logger.info(f"Deleted auto translation rule {rule_id}")


@router.patch("/{rule_id}/toggle", response_model=AutoTranslationRuleResponse, summary="Toggle rule enabled status")
async def toggle_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AutoTranslationRuleResponse:
    """
    Toggle the enabled status of a rule.

    Args:
        rule_id: Rule UUID

    Returns:
        Updated rule details
    """
    stmt = sa.select(AutoTranslationRule).where(
        AutoTranslationRule.id == rule_id,
        AutoTranslationRule.user_id == current_user.id,
    )
    rule = db.scalar(stmt)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    rule.enabled = not rule.enabled
    db.commit()
    db.refresh(rule)

    logger.info(f"Toggled auto translation rule {rule.id} to enabled={rule.enabled}")

    return AutoTranslationRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        enabled=rule.enabled,
        jellyfin_library_ids=json.loads(rule.jellyfin_library_ids),
        source_lang=rule.source_lang,
        target_langs=json.loads(rule.target_langs),
        auto_start=rule.auto_start,
        priority=rule.priority,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )
