"""
Database initialization - create initial admin user if needed.
"""

import logging

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


def init_database(db: Session) -> None:
    """
    Initialize database with required data.

    Creates an initial admin user if no users exist.

    Args:
        db: Database session
    """
    # Check if any users exist
    stmt = sa.select(sa.func.count()).select_from(User)
    user_count = db.scalar(stmt) or 0

    if user_count == 0:
        logger.info("No users found in database. Creating initial admin user...")

        # Generate or use configured password
        if settings.initial_admin_password:
            password = settings.initial_admin_password
            logger.info("Using configured initial admin password")
        else:
            password = AuthService.generate_random_password(16)
            logger.warning(f"Generated random initial admin password: {password}")
            logger.warning("IMPORTANT: Save this password! It won't be shown again.")
            logger.warning(f"Username: {settings.initial_admin_username}")
            logger.warning(f"Password: {password}")

        # Create admin user
        admin = AuthService.create_user(
            db=db, username=settings.initial_admin_username, password=password, is_admin=True
        )

        logger.info(f"Created initial admin user: {admin.username} (ID: {admin.id})")

        # Print credentials one more time for visibility
        if not settings.initial_admin_password:
            print("\n" + "=" * 80)
            print("INITIAL ADMIN CREDENTIALS")
            print("=" * 80)
            print(f"Username: {settings.initial_admin_username}")
            print(f"Password: {password}")
            print("=" * 80)
            print("Please save these credentials and change the password after first login!")
            print("=" * 80 + "\n")
    else:
        logger.info(f"Database already initialized with {user_count} user(s)")
