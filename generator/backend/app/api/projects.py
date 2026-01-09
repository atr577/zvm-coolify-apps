from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models import Project
from app.models.user import User, WorkspaceMember
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.core.deps import get_current_user

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

    db_project = Project(
        name=project.name,
        description=project.description,
        story_template=project.story_template,
        platforms=project.platforms,
        duration=project.duration,
        workspace_id=workspace_id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список проектов из всех workspaces пользователя"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if not workspace_ids:
        return []

    projects = db.query(Project).filter(
        Project.workspace_id.in_(workspace_ids)
    ).offset(skip).limit(limit).all()
    return projects


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
