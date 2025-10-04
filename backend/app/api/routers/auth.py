"""
Authentication API endpoints.
"""

from datetime import timedelta
from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import sqlalchemy as sa

from app.core.db import get_db
from app.core.config import settings
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    ChangePasswordRequest,
    UpdateProfileRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    payload = AuthService.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    stmt = sa.select(User).where(User.username == username)
    user = db.scalar(stmt)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    return user


async def get_current_user_sse(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    token: str | None = None,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current user for SSE endpoints.
    Supports both Bearer token (header) and query parameter token.

    Args:
        credentials: Optional Bearer token from Authorization header
        token: Optional token from query parameter
        db: Database session

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Try to get token from header first, then query parameter
    auth_token = None
    if credentials:
        auth_token = credentials.credentials
    elif token:
        auth_token = token
    
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = AuthService.decode_token(auth_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    stmt = sa.select(User).where(User.username == username)
    user = db.scalar(stmt)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Authenticate user and return JWT token.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        TokenResponse: Access token and user info

    Raises:
        HTTPException: If authentication fails
    """
    user = AuthService.authenticate_user(db, request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    # Update last login time
    AuthService.update_last_login(db, user)

    # Create access token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    logger.info(f"User {user.username} logged in successfully")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get current user profile.

    Args:
        current_user: Authenticated user

    Returns:
        UserResponse: User profile information
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
def update_profile(
    request: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Update current user profile.

    Args:
        request: Profile update data
        current_user: Authenticated user
        db: Database session

    Returns:
        UserResponse: Updated user profile
    """
    if request.email is not None:
        current_user.email = request.email

    db.commit()
    db.refresh(current_user)

    logger.info(f"User {current_user.username} updated their profile")

    return UserResponse.model_validate(current_user)


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Change current user's password.

    Args:
        request: Password change data
        current_user: Authenticated user
        db: Database session

    Raises:
        HTTPException: If old password is incorrect
    """
    # Verify old password
    if not AuthService.verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    # Change password
    AuthService.change_password(db, current_user, request.new_password)

    logger.info(f"User {current_user.username} changed their password")

    return {"message": "Password changed successfully"}


@router.post("/logout")
def logout(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Logout current user.

    Note: Since we're using stateless JWT tokens, this is mainly for
    logging purposes. Client should discard the token.

    Args:
        current_user: Authenticated user
    """
    logger.info(f"User {current_user.username} logged out")

    return {"message": "Logged out successfully"}
