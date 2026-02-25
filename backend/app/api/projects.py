from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.db.base import get_db
from app.models import Project
from app.models.user import User, SocialAccount, WorkspaceMember
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.project import BindSocialAccountRequest, BindYouTubeAccountRequest
from app.models.youtube_account import YouTubeAccount, YouTubeAccountStatus
from app.schemas.pagination import PaginatedResponse
from app.core.deps import get_current_user
from app.services.prompt_builders import DEFAULT_SYSTEM_PROMPTS
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_project_platforms(project: Project) -> List[str]:
    """Derive platforms from bound social accounts with fallback to project.platforms.

    Rules:
    - Active bound accounts take priority over project.platforms
    - is_active=False accounts are excluded
    - If all accounts inactive → fallback to project.platforms
    - If both empty → return empty list (graceful skip)
    """
    if project.social_accounts:
        active_platforms = list(set(
            acc.platform for acc in project.social_accounts
            if acc.is_active
        ))
        if active_platforms:
            return active_platforms
    return project.platforms or []


def get_user_workspace_ids(db: Session, user_id: int) -> List[int]:
    """Get all workspace IDs the user is a member of"""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [m.workspace_id for m in memberships]


def user_has_workspace_access(db: Session, user_id: int, workspace_id: int) -> bool:
    """Check if user has access to a workspace"""
    return db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first() is not None


@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новый проект (template container)"""
    # Get user's first workspace (for now, use first available workspace)
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if not workspace_ids:
        raise HTTPException(status_code=400, detail="User has no workspace")

    workspace_id = project.workspace_id if hasattr(project, 'workspace_id') and project.workspace_id else workspace_ids[0]

    if workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="No access to this workspace")

    # Validate remix project fields
    if project.project_type == "remix":
        placeholders = project.placeholders or []
        suggestions = project.placeholder_suggestions or {}

        # Check all placeholders have suggestions
        missing = set(placeholders) - set(suggestions.keys())
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing suggestions for placeholders: {missing}")

        # Check no empty suggestions
        empty = [p for p in placeholders if not suggestions.get(p)]
        if empty:
            raise HTTPException(status_code=400, detail=f"Empty suggestions for placeholders: {empty}")

    # Merge user-provided system_prompts with defaults
    system_prompts = {**DEFAULT_SYSTEM_PROMPTS}
    if project.system_prompts:
        for key, value in project.system_prompts.items():
            if value:  # Only override if user provided non-empty value
                system_prompts[key] = value

    db_project = Project(
        name=project.name,
        description=project.description,
        story_template=project.story_template,
        platforms=project.platforms,
        duration=project.duration,
        aspect_ratio=project.aspect_ratio,
        audio_mode=project.audio_mode,
        audio_provider=project.audio_provider,
        project_type=project.project_type,
        system_prompts=system_prompts,
        workspace_id=workspace_id,
        user_id=current_user.id,
        # Remix-specific fields
        source_video_ids=project.source_video_ids,
        scenario_template=project.scenario_template,
        placeholders=project.placeholders,
        placeholder_suggestions=project.placeholder_suggestions,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    workspace_id: Optional[int] = Query(None, description="Filter by workspace"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaginatedResponse[ProjectResponse]:
    """Получить список проектов с пагинацией"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if not workspace_ids:
        return PaginatedResponse(items=[], total=0, page=page, limit=limit)

    # Filter by specific workspace if provided
    filter_workspaces = workspace_ids
    if workspace_id:
        if workspace_id not in workspace_ids:
            raise HTTPException(status_code=403, detail="No access to this workspace")
        filter_workspaces = [workspace_id]

    # Count total
    total = db.query(Project).filter(
        Project.workspace_id.in_(filter_workspaces)
    ).count()

    # Get paginated projects
    offset = (page - 1) * limit
    projects = db.query(Project).filter(
        Project.workspace_id.in_(filter_workspaces)
    ).order_by(Project.created_at.desc()).offset(offset).limit(limit).all()

    return PaginatedResponse(
        items=projects,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить проект по ID"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    project = db.query(Project).options(
        joinedload(Project.social_accounts)
    ).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить проект (редактирование шаблона)"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить проект (и все его видео через cascade)"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}


@router.get("/audio-options")
async def get_audio_options_endpoint():
    """
    Get available audio providers and their configuration.

    Returns:
        Dict with:
            - types: list of audio types (none, scene, music, voiceover, auto)
            - providers: mapping of audio_mode to available providers
            - defaults: mapping of audio_mode to default provider
            - ai_music_available: whether ai_music provider can be used
    """
    from app.core.audio_config import get_audio_options

    return get_audio_options()


# --- Social Account Binding ---


@router.post("/{project_id}/social-accounts", response_model=ProjectResponse)
async def bind_social_account(
    project_id: int,
    request: BindSocialAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bind a social account to a project. Workspace-level access: any member can bind any account in the workspace."""
    workspace_ids = get_user_workspace_ids(db, current_user.id)

    project = db.query(Project).options(
        joinedload(Project.social_accounts)
    ).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find social account — must belong to a user in the same workspace
    social_account = db.query(SocialAccount).join(
        WorkspaceMember, WorkspaceMember.user_id == SocialAccount.user_id
    ).filter(
        SocialAccount.id == request.social_account_id,
        WorkspaceMember.workspace_id == project.workspace_id
    ).first()
    if not social_account:
        raise HTTPException(status_code=404, detail="Social account not found in this workspace")

    # Check if already bound
    if social_account in project.social_accounts:
        raise HTTPException(status_code=409, detail="Account already bound to project")

    project.social_accounts.append(social_account)
    db.commit()
    db.refresh(project)

    logger.info(f"Bound social account {social_account.id} (@{social_account.username}) to project {project.id}")
    return project


@router.delete("/{project_id}/social-accounts/{account_id}")
async def unbind_social_account(
    project_id: int,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unbind a social account from a project. Workspace-level access."""
    workspace_ids = get_user_workspace_ids(db, current_user.id)

    project = db.query(Project).options(
        joinedload(Project.social_accounts)
    ).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    social_account = next(
        (acc for acc in project.social_accounts if acc.id == account_id),
        None
    )
    if not social_account:
        raise HTTPException(status_code=404, detail="Account not bound to this project")

    project.social_accounts.remove(social_account)
    db.commit()

    logger.info(f"Unbound social account {account_id} from project {project.id}")
    return {"message": "Social account unbound successfully"}


# --- Workspace YouTube Account Binding ---

@router.patch("/{project_id}/youtube-account", response_model=ProjectResponse)
async def bind_youtube_account(
    project_id: int,
    request: BindYouTubeAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bind or unbind a workspace YouTubeAccount to a project."""
    workspace_ids = get_user_workspace_ids(db, current_user.id)

    project = db.query(Project).options(
        joinedload(Project.social_accounts)
    ).filter(
        Project.id == project_id,
        Project.workspace_id.in_(workspace_ids)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.youtube_account_id is not None:
        yt_account = db.query(YouTubeAccount).filter(
            YouTubeAccount.id == request.youtube_account_id,
            YouTubeAccount.workspace_id == project.workspace_id,
            YouTubeAccount.token_status == YouTubeAccountStatus.ACTIVE.value,
        ).first()
        if not yt_account:
            raise HTTPException(status_code=404, detail="YouTube account not found in this workspace")
        project.youtube_account_id = yt_account.id
        logger.info(f"Bound workspace YouTubeAccount {yt_account.id} ({yt_account.channel_title}) to project {project.id}")
    else:
        project.youtube_account_id = None
        logger.info(f"Unbound workspace YouTubeAccount from project {project.id}")

    db.commit()
    db.refresh(project)
    return project
