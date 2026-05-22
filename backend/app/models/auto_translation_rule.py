"""
Auto Translation Rule model.

Manages automatic translation rules for media library scanning.
"""

from typing import Optional
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.types import GUID


class AutoTranslationRule(BaseModel):
    """
    Auto translation rule for automatic job creation and execution.

    When media library is scanned, if a job matches the rule conditions,
    it can be automatically started based on the rule configuration.
    """

    __tablename__ = "auto_translation_rule"

    # Rule owner
    user_id: Mapped[GUID] = mapped_column(
        GUID, ForeignKey("user.id"), nullable=False, index=True
    )

    # Rule name
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Whether the rule is enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Jellyfin library IDs to monitor (JSON array: ["lib1", "lib2"])
    # Empty array means all libraries
    jellyfin_library_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Source language filter (BCP-47 code or null for all)
    source_lang: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Target languages (JSON array: ["zh-CN", "en", "ja"])
    target_langs: Mapped[str] = mapped_column(Text, nullable=False)

    # Whether to auto-start matched jobs
    auto_start: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Job priority (1-10, higher = more priority)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
