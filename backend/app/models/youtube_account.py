from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base import Base


class YouTubeAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    ERROR = "error"


class YouTubeAccount(Base):
    __tablename__ = "youtube_accounts"

    id = Column(Integer, primary_key=True, index=True)
    google_account_id = Column(String(255), unique=True, nullable=False, index=True)  # "sub" from Google userinfo
    google_email = Column(String(255), nullable=False)
    channel_id = Column(String(255), unique=True, nullable=False, index=True)
    channel_title = Column(String(255), nullable=False)
    channel_thumbnail_url = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=False)
    access_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=False)  # space-separated full URIs
    token_status = Column(String(50), default=YouTubeAccountStatus.ACTIVE.value)
    last_token_refresh = Column(DateTime, nullable=True)
    linked_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)

    workspace = relationship("Workspace")

    def __repr__(self):
        return f"<YouTubeAccount(id={self.id}, channel='{self.channel_title}', email='{self.google_email}')>"
