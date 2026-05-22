"""
System settings model.

Key-value store for system configuration and runtime settings.
"""

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.models.base import Base


class Setting(Base):
    """
    System settings stored as key-value pairs.

    This allows dynamic configuration without requiring application restart.
    """

    __tablename__ = "setting"

    # Setting key (primary key)
    key: Mapped[str] = mapped_column(String(100), primary_key=True, nullable=False)

    # Setting value (stored as text, JSON for complex values)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Description of the setting
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Setting category (for grouping)
    category: Mapped[str] = mapped_column(String(50), nullable=True, index=True)

    # Is this setting editable through UI?
    is_editable: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Setting data type: string | int | float | bool | json
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)

    # Updated timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    # Updated by user/system
    updated_by: Mapped[str] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<Setting(key={self.key}, value={self.value[:50]}...)>"
