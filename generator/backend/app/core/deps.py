from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.services.media.base import (
    ImageServiceProtocol,
    VideoServiceProtocol,
    AudioServiceProtocol,
)
from app.services.providers.kling import (
    KlingImageService,
    KlingVideoService,
    KlingAudioService,
)

security = HTTPBearer()

# Media service singletons (can be configured via settings in future)
_image_service: Optional[ImageServiceProtocol] = None
_video_service: Optional[VideoServiceProtocol] = None
_audio_service: Optional[AudioServiceProtocol] = None


def get_image_service() -> ImageServiceProtocol:
    """Get image generation service (currently KLING)."""
    global _image_service
    if _image_service is None:
        _image_service = KlingImageService()
    return _image_service


def get_video_service() -> VideoServiceProtocol:
    """Get video generation service (currently KLING)."""
    global _video_service
    if _video_service is None:
        _video_service = KlingVideoService()
    return _video_service


def get_audio_service() -> AudioServiceProtocol:
    """Get audio generation service (currently KLING)."""
    global _audio_service
    if _audio_service is None:
        _audio_service = KlingAudioService()
    return _audio_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    if credentials is None:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
