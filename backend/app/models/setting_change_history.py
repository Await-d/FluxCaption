"""
Setting Change History Model.

Tracks all changes to system settings for audit trail.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Index
from app.models.base import Base
from app.models.types import GUID


class SettingChangeHistory(Base):
    """
    Setting change history record.

    Stores audit trail of all configuration changes.
    """

    __tablename__ = "setting_change_history"

    id = Column(GUID, primary_key=True)
    setting_key = Column(String(255), nullable=False, index=True)
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=False)
    changed_by = Column(String(255), nullable=False)
    change_reason = Column(Text, nullable=True)  # Unbounded text for detailed change reasons
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Composite index for efficient queries
    __table_args__ = (
        Index("idx_setting_history_key", "setting_key", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SettingChangeHistory(id={self.id}, "
            f"key={self.setting_key}, "
            f"changed_by={self.changed_by}, "
            f"created_at={self.created_at})>"
        )
