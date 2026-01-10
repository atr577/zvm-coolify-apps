from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.db.base import get_db
from app.models import Video, Project
from app.models.user import User, WorkspaceMember
from app.schemas import VideoCreate, VideoUpdate, VideoResponse
from app.schemas.pagination import PaginatedResponse
from app.core.deps import get_current_user

router = APIRouter()


def get_user_workspace_ids(db: Session, user_id: int) -> List[int]:
    """Get all workspace IDs the user is a member of"""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [m.workspace_id for m in memberships]


def verify_video_access(db: Session, video: Video, user_id: int):
    """Verify user has access to video via workspace"""
    workspace_ids = get_user_workspace_ids(db, user_id)
    if video.project.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("/", response_model=VideoResponse)
async def create_video(
    video: VideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новое видео"""
    # Проверить что проект существует и у пользователя есть доступ
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    project = db.query(Project).filter(
        Project.id == video.project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_video = Video(
        project_id=video.project_id,
        title=video.title,
        workflow_mode=video.workflow_mode,
        content_variables=video.content_variables
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video


@router.get("/project/{project_id}")
async def list_videos_by_project(
    project_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaginatedResponse[VideoResponse]:
    """Получить видео проекта с пагинацией"""
    # Проверить что проект существует и у пользователя есть доступ
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count total
    total = db.query(Video).filter(Video.project_id == project_id).count()

    # Get paginated videos with eager loading
    offset = (page - 1) * limit
    videos = db.query(Video).filter(
        Video.project_id == project_id
    ).options(
        joinedload(Video.project)
    ).order_by(Video.created_at.desc()).offset(offset).limit(limit).all()

    return PaginatedResponse(
        items=videos,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить видео по ID"""
    video = db.query(Video).options(
        joinedload(Video.project)
    ).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Проверить доступ через workspace (project уже загружен)
    verify_video_access(db, video, current_user.id)

    return video


@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить видео"""
    video = db.query(Video).options(
        joinedload(Video.project)
    ).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Проверить доступ через workspace
    verify_video_access(db, video, current_user.id)

    update_data = video_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video, field, value)

    db.commit()
    db.refresh(video)
    return video


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить видео (и все его workflow steps через cascade)"""
    video = db.query(Video).options(
        joinedload(Video.project)
    ).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Проверить доступ через workspace
    verify_video_access(db, video, current_user.id)

    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}
