from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.base import get_db
from app.models import Project
from app.models.user import User, WorkspaceMember
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.pagination import PaginatedResponse
from app.core.deps import get_current_user
from app.services.prompt_builders import DEFAULT_SYSTEM_PROMPTS

router = APIRouter()


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


@router.post("/", response_model=ProjectResponse)
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


@router.get("/")
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
    project = db.query(Project).filter(
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
