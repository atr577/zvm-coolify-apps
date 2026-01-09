from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.db.base import Base
import enum
import secrets


class UserRole(str, enum.Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"


class SocialPlatform(str, enum.Enum):
    """Supported social platforms"""
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class InviteType(str, enum.Enum):
    """Invite types"""
    STANDALONE = "standalone"  # Creates user with own workspace
    WORKSPACE = "workspace"    # Adds user to existing workspace


class WorkspaceRole(str, enum.Enum):
    """Workspace member roles"""
    OWNER = "owner"
    MEMBER = "member"


class User(Base):
    """
    User - основной пользователь сервиса
    Имеет email/password аутентификацию
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(50), default=UserRole.USER.value)
    can_create_workspace = Column(Boolean, default=True)  # False for workspace-invited users

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class SocialAccount(Base):
    """
    SocialAccount - OAuth аккаунт социальной сети
    Один пользователь может иметь несколько аккаунтов для одной платформы
    """
    __tablename__ = "social_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Platform info
    platform = Column(String(50), nullable=False, index=True)  # instagram, tiktok, youtube
    platform_user_id = Column(String(255), nullable=False)  # ID пользователя в соц. сети
    username = Column(String(255), nullable=True)  # @username в соц. сети
    display_name = Column(String(255), nullable=True)  # Отображаемое имя
    profile_picture = Column(Text, nullable=True)  # URL аватарки

    # OAuth credentials
    access_token = Column(Text, nullable=False)  # OAuth access token
    refresh_token = Column(Text, nullable=True)  # OAuth refresh token (если поддерживается)
    token_expires_at = Column(DateTime, nullable=True)  # Когда истекает токен

    # Additional platform-specific data
    platform_data = Column(JSON, nullable=True)  # Дополнительные данные (например, business_account_id для Instagram)

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="social_accounts")
    projects = relationship("Project", secondary="project_social_accounts", back_populates="social_accounts")

    def __repr__(self):
        return f"<SocialAccount(id={self.id}, platform='{self.platform}', username='{self.username}')>"

    @property
    def is_token_expired(self):
        """Check if OAuth token is expired"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at


class Workspace(Base):
    """Workspace - рабочее пространство для проектов"""
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}')>"


class WorkspaceMember(Base):
    """WorkspaceMember - участник рабочего пространства"""
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default=WorkspaceRole.MEMBER.value)

    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")

    def __repr__(self):
        return f"<WorkspaceMember(workspace_id={self.workspace_id}, user_id={self.user_id}, role='{self.role}')>"


class Invite(Base):
    """Invite - приглашение для регистрации"""
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    type = Column(SQLEnum(InviteType), nullable=False, default=InviteType.STANDALONE)

    email = Column(String(255), nullable=True)  # Optional pre-set email
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)  # For workspace invites

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    used_at = Column(DateTime, nullable=True)
    used_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    used_by = relationship("User", foreign_keys=[used_by_id])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])

    def __repr__(self):
        return f"<Invite(id={self.id}, type='{self.type}', used={self.used_at is not None})>"

    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    @property
    def is_expired(self):
        """Check if invite is expired"""
        return datetime.utcnow() >= self.expires_at

    @property
    def is_used(self):
        """Check if invite has been used"""
        return self.used_at is not None

    @property
    def is_valid(self):
        """Check if invite is valid (not expired and not used)"""
        return not self.is_expired and not self.is_used
