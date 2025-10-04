"""
Pydantic schemas for authentication.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_serializer


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    username: str
    email: str | None
    is_active: bool
    is_admin: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer('id')
    def serialize_id(self, id: UUID, _info):
        return str(id)


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


class UpdateProfileRequest(BaseModel):
    """Update profile request schema."""
    email: str | None = None
