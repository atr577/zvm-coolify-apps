"""
Auth-required routes for workspace YouTube accounts.
GET /api/youtube-accounts/workspace → list YouTubeAccounts for current user's workspace
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.user import User, WorkspaceMember
from app.models.youtube_account import YouTubeAccount, YouTubeAccountStatus

router = APIRouter()


class WorkspaceYouTubeAccountResponse(BaseModel):
    id: int
    platform: str = "youtube"
    source: str = "workspace"
    channel_id: str
    channel_title: str
    channel_handle: Optional[str]
    channel_thumbnail_url: Optional[str]
    google_email: str
    token_status: str
    linked_at: datetime

    class Config:
        from_attributes = True


@router.get("/workspace", response_model=List[WorkspaceYouTubeAccountResponse])
def list_workspace_youtube_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active YouTubeAccounts for the current user's workspaces."""
    workspace_ids = [
        m.workspace_id
        for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    ]
    if not workspace_ids:
        return []

    accounts = db.query(YouTubeAccount).filter(
        YouTubeAccount.workspace_id.in_(workspace_ids),
        YouTubeAccount.token_status == YouTubeAccountStatus.ACTIVE.value,
    ).all()

    return accounts
