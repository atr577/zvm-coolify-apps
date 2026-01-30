from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class InviteTypeEnum(str, Enum):
    STANDALONE = "standalone"
    WORKSPACE = "workspace"


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None
    invite_token: str  # Required - no open registration


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
    can_create_workspace: bool
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


# Workspace schemas
class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class WorkspaceUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    member_count: Optional[int] = None
    is_owner: Optional[bool] = None

    class Config:
        from_attributes = True


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class WorkspaceDetailResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    members: List[WorkspaceMemberResponse] = []
    is_owner: bool = False

    class Config:
        from_attributes = True


# Invite schemas
class InviteCreateRequest(BaseModel):
    type: InviteTypeEnum
    email: Optional[EmailStr] = None  # Optional email restriction
    workspace_id: Optional[int] = None  # Required for workspace invites
    expires_in_hours: int = Field(default=72, ge=1, le=720)  # 1 hour to 30 days


class WorkspaceInviteCreate(BaseModel):
    """Simplified invite creation for workspace owners (type and workspace_id are implicit)"""
    email: Optional[EmailStr] = None
    expires_in_hours: int = Field(default=72, ge=1, le=720)


class InviteResponse(BaseModel):
    id: int
    token: str
    type: InviteTypeEnum
    email: Optional[str]
    workspace_id: Optional[int]
    workspace_name: Optional[str] = None
    created_by_id: int
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime]
    used_by_id: Optional[int]
    is_valid: bool

    class Config:
        from_attributes = True


class InviteValidateResponse(BaseModel):
    valid: bool
    type: Optional[InviteTypeEnum] = None
    email: Optional[str] = None
    workspace_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


# Setup schemas (first admin creation)
class SetupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None


class SetupResponse(BaseModel):
    user: UserResponse
    workspace: WorkspaceResponse
    message: str = "Admin user created and workspace initialized"
