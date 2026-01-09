from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import enum


class UserRole(str, enum.Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"


class SocialPlatform(str, enum.Enum):
    """Supported social platforms"""
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

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
