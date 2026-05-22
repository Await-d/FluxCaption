"""
Custom SQLAlchemy types for cross-database compatibility.

Provides GUID type that works consistently across PostgreSQL, MySQL, SQLite, and SQL Server.
"""

import uuid
from typing import Any
import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses CHAR(36) to store UUIDs as strings, ensuring compatibility across
    PostgreSQL, MySQL, SQLite, and SQL Server.

    On PostgreSQL, this could be optimized to use native UUID type, but
    we choose CHAR(36) for simplicity and consistency across all databases.

    Usage:
        class MyModel(Base):
            __tablename__ = "my_table"

            id = Column(GUID, primary_key=True, default=uuid.uuid4)
    """

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: sa.engine.Dialect) -> str | None:
        """
        Convert Python UUID to database string representation.

        Args:
            value: UUID value to convert (can be str, UUID, or None)
            dialect: SQLAlchemy dialect (not used, but required by interface)

        Returns:
            str | None: String representation of UUID, or None
        """
        if value is None:
            return None

        if isinstance(value, uuid.UUID):
            return str(value)

        # If it's already a string, ensure it's a valid UUID
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError, TypeError):
            raise ValueError(f"Invalid UUID value: {value}")

    def process_result_value(self, value: Any, dialect: sa.engine.Dialect) -> uuid.UUID | None:
        """
        Convert database string representation to Python UUID.

        Args:
            value: String value from database
            dialect: SQLAlchemy dialect (not used, but required by interface)

        Returns:
            uuid.UUID | None: UUID object, or None
        """
        if value is None:
            return None

        if isinstance(value, uuid.UUID):
            return value

        # Strip whitespace from database value
        if isinstance(value, str):
            value = value.strip()

        try:
            # Try parsing as-is first (handles standard UUID format with hyphens)
            return uuid.UUID(value)
        except (ValueError, AttributeError, TypeError):
            # If that fails, try parsing as hex string without hyphens
            # UUID constructor accepts hex parameter which handles 32-char hex strings
            try:
                if isinstance(value, str) and len(value) == 32:
                    # This is a UUID without hyphens, parse it using hex parameter
                    return uuid.UUID(hex=value)
            except (ValueError, AttributeError, TypeError):
                pass
            raise ValueError(f"Invalid UUID string in database: {value}")

    def process_literal_param(self, value: Any, dialect: sa.engine.Dialect) -> str:
        """Process a literal parameter value."""
        if value is None:
            return "NULL"
        return f"'{self.process_bind_param(value, dialect)}'"

    @property
    def python_type(self) -> type:
        """Return the Python type for this database type."""
        return uuid.UUID


# =============================================================================
# Helper Functions
# =============================================================================

def generate_uuid() -> uuid.UUID:
    """
    Generate a new UUID v4.

    Returns:
        uuid.UUID: A new random UUID
    """
    return uuid.uuid4()


def uuid_to_str(value: uuid.UUID | str | None) -> str | None:
    """
    Convert UUID to string representation.

    Args:
        value: UUID value (can be UUID object, string, or None)

    Returns:
        str | None: String representation of UUID, or None
    """
    if value is None:
        return None

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, str):
        # Validate and normalize
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid UUID string: {value}")

    raise TypeError(f"Expected UUID or str, got {type(value)}")


def str_to_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    """
    Convert string to UUID object.

    Args:
        value: String or UUID value (or None)

    Returns:
        uuid.UUID | None: UUID object, or None
    """
    if value is None:
        return None

    if isinstance(value, uuid.UUID):
        return value

    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid UUID string: {value}")

    raise TypeError(f"Expected str or UUID, got {type(value)}")


def is_valid_uuid(value: Any) -> bool:
    """
    Check if a value is a valid UUID.

    Args:
        value: Value to check

    Returns:
        bool: True if value is a valid UUID, False otherwise
    """
    if isinstance(value, uuid.UUID):
        return True

    if isinstance(value, str):
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

    return False
