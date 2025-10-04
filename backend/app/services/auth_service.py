"""
Authentication service for user management and JWT token handling.
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import string

from jose import JWTError, jwt
from passlib.context import CryptContext
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            bool: True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            str: JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decode and verify a JWT token.

        Args:
            token: JWT token string

        Returns:
            Optional[dict]: Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user by username and password.

        Args:
            db: Database session
            username: Username
            password: Plain text password

        Returns:
            Optional[User]: User object if authentication succeeds, None otherwise
        """
        stmt = sa.select(User).where(User.username == username)
        user = db.scalar(stmt)

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    def create_user(
        db: Session,
        username: str,
        password: str,
        email: Optional[str] = None,
        is_admin: bool = False
    ) -> User:
        """
        Create a new user.

        Args:
            db: Database session
            username: Username
            password: Plain text password
            email: Email address
            is_admin: Whether user is admin

        Returns:
            User: Created user object
        """
        password_hash = AuthService.get_password_hash(password)

        user = User(
            username=username,
            password_hash=password_hash,
            email=email,
            is_admin=is_admin,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        """
        Update user's last login timestamp.

        Args:
            db: Database session
            user: User object
        """
        user.last_login_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def change_password(db: Session, user: User, new_password: str) -> None:
        """
        Change user's password.

        Args:
            db: Database session
            user: User object
            new_password: New plain text password
        """
        user.password_hash = AuthService.get_password_hash(new_password)
        db.commit()

    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """
        Generate a secure random password.

        Args:
            length: Password length (max 72 for bcrypt compatibility)

        Returns:
            str: Random password
        """
        # Limit length to 72 bytes for bcrypt compatibility
        length = min(length, 72)
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
