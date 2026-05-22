"""
Base model class for all database models.

Provides common fields and functionality for all models.
"""

from datetime import datetime
from typing import Any
import uuid
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy import DateTime

from app.models.types import GUID


class Base(DeclarativeBase):
    """
    Base class for all database models.

    Provides:
    - Automatic table name generation
    - Common GUID primary key
    - Created/updated timestamp tracking
    - String representation
    """

    # Tell SQLAlchemy not to create a table for this base class
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.

        Converts CamelCase to snake_case.
        Example: MediaAsset -> media_asset
        """
        import re
        name = cls.__name__
        # Insert underscores before uppercase letters and convert to lowercase
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()

    def dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            dict: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """
        String representation of the model.

        Returns:
            str: String representation
        """
        attrs = []
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            attrs.append(f"{column.name}={value!r}")

        return f"{self.__class__.__name__}({', '.join(attrs)})"


class TimestampMixin:
    """
    Mixin for models that need created_at and updated_at timestamps.

    All timestamps are stored in UTC.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )


class IDMixin:
    """
    Mixin for models that need a GUID primary key.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


# =============================================================================
# Common Base Classes
# =============================================================================

class BaseModel(Base, IDMixin, TimestampMixin):
    """
    Base model with ID and timestamp fields.

    Most models should inherit from this class.
    """

    __abstract__ = True


class BaseModelWithoutTimestamp(Base, IDMixin):
    """
    Base model with ID but without timestamps.

    Use this for models that don't need timestamp tracking.
    """

    __abstract__ = True
