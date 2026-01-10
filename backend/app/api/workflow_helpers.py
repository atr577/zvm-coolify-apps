"""
Helper functions for workflow API endpoints.
Extracted from workflow.py for better maintainability.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.video import Video
from app.models.user import User, WorkspaceMember


def build_camera_control(camera_movement: dict) -> dict | None:
    """
    Convert camera_movement from scenario to camera_control for KLING API.

    Args:
        camera_movement: Dict with type, speed, description from scenario

    Returns:
        camera_control dict for KLING or None if static
    """
    if not camera_movement or not isinstance(camera_movement, dict):
        return None

    camera_type = camera_movement.get("type", "static")
    if camera_type == "static":
        return None

    return {
        "type": camera_type,
        "config": {
            "horizontal": 0,
            "vertical": 0,
            "pan": -5 if camera_type == "pan_left" else 5 if camera_type == "pan_right" else 0,
            "tilt": 5 if camera_type == "tilt_up" else -5 if camera_type == "tilt_down" else 0,
            "zoom": 5 if camera_type == "zoom_in" else -5 if camera_type == "zoom_out" else 0,
            "roll": 0
        }
    }


def get_user_workspace_ids(db: Session, user_id: int) -> List[int]:
    """Get all workspace IDs the user is a member of."""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [m.workspace_id for m in memberships]


def verify_video_ownership(db: Session, video: Video, current_user: User):
    """Check video access through workspace membership."""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if video.project.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Access denied: you don't own this video")


def get_video_or_404(db: Session, video_id: int) -> Video:
    """Get video by ID or raise 404."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


def get_video_with_auth(db: Session, video_id: int, current_user: User) -> Video:
    """Get video by ID, verify ownership, or raise error."""
    video = get_video_or_404(db, video_id)
    verify_video_ownership(db, video, current_user)
    return video
