from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class SocialAccountResponse(BaseModel):
    id: int
    platform: str
    platform_user_id: str
    username: Optional[str]
    display_name: Optional[str]
    profile_picture: Optional[str]
    is_active: bool
    created_at: datetime
    is_token_expired: bool

    class Config:
        from_attributes = True


class SocialAccountCreate(BaseModel):
    platform: str
    access_token: str
    refresh_token: Optional[str] = None
    platform_user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_picture: Optional[str] = None
    platform_data: Optional[dict] = None
