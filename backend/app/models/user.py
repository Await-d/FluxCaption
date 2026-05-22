"""
User model for authentication and authorization.
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime

from app.models.base import BaseModel


class User(BaseModel):
    """
    User model for authentication.

    Attributes:
        username: Unique username for login
        password_hash: Hashed password (bcrypt)
        email: User email address (optional)
        is_active: Whether the user account is active
        is_admin: Whether the user has admin privileges
        last_login_at: Last login timestamp
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username!r}, is_admin={self.is_admin})"
