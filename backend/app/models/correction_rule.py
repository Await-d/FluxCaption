"""
Correction Rule model for translation post-processing.
"""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, Integer

from app.models.base import BaseModel


class CorrectionRule(BaseModel):
    """
    Translation correction rule model.

    Used for automatic correction of translation output.
    Can replace text patterns, fix terminology, etc.

    Attributes:
        name: Rule name/description
        source_pattern: Pattern to match (can be regex if is_regex=True)
        target_text: Replacement text
        is_regex: Whether source_pattern is a regex pattern
        is_case_sensitive: Whether matching is case-sensitive
        is_active: Whether this rule is currently active
        source_lang: Source language code (optional, apply to all if None)
        target_lang: Target language code (optional, apply to all if None)
        priority: Rule application priority (higher = earlier)
        created_by: User ID who created this rule
    """

    __tablename__ = "correction_rules"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_pattern: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    target_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_regex: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_case_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    source_lang: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Source language code (BCP-47), None = apply to all"
    )

    target_lang: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Target language code (BCP-47), None = apply to all"
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Higher priority rules are applied first"
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Username of the creator"
    )

    def __repr__(self) -> str:
        return f"CorrectionRule(id={self.id}, name={self.name!r}, is_active={self.is_active})"
