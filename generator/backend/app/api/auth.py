from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.db.base import get_db
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    Token,
    UserResponse,
    InviteCreateRequest,
    InviteResponse,
    InviteValidateResponse,
    InviteTypeEnum,
    WorkspaceResponse,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceDetailResponse,
    WorkspaceMemberResponse
)
from app.models.user import User, Invite, InviteType, Workspace, WorkspaceMember, WorkspaceRole, UserRole
from app.core.security import hash_password, verify_password, create_access_token, needs_rehash
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user with invite token"""
    # Validate invite token
    invite = db.query(Invite).filter(Invite.token == request.invite_token).first()
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite token")

    if not invite.is_valid:
        if invite.is_used:
            raise HTTPException(status_code=400, detail="Invite has already been used")
        if invite.is_expired:
            raise HTTPException(status_code=400, detail="Invite has expired")

    # Check email restriction
    if invite.email and invite.email.lower() != request.email.lower():
        raise HTTPException(status_code=400, detail="Email does not match invite")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    can_create_workspace = invite.type == InviteType.STANDALONE
    new_user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        is_active=True,
        is_verified=True,  # Verified via invite
        role="user",
        can_create_workspace=can_create_workspace
    )
    db.add(new_user)
    db.flush()  # Get user ID

    if invite.type == InviteType.STANDALONE:
        # Create workspace for standalone invite
        workspace = Workspace(
            name=f"{request.full_name or request.email}'s Workspace",
            owner_id=new_user.id
        )
        db.add(workspace)
        db.flush()

        # Add user as workspace owner
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=new_user.id,
            role=WorkspaceRole.OWNER.value
        )
        db.add(member)
    else:
        # Workspace invite - add to existing workspace
        if not invite.workspace_id:
            raise HTTPException(status_code=400, detail="Invalid workspace invite")

        member = WorkspaceMember(
            workspace_id=invite.workspace_id,
            user_id=new_user.id,
            role=WorkspaceRole.MEMBER.value
        )
        db.add(member)

    # Mark invite as used
    invite.used_at = datetime.utcnow()
    invite.used_by_id = new_user.id

    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Auto-migrate legacy SHA256 passwords to bcrypt
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(request.password)

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Create access token
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email}
    )

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return current_user


# ============== Invite Endpoints ==============

@router.post("/invites", response_model=InviteResponse)
def create_invite(
    request: InviteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new invite (admin only)"""
    # Validate workspace invite
    workspace_name = None
    if request.type == InviteTypeEnum.WORKSPACE:
        if not request.workspace_id:
            raise HTTPException(status_code=400, detail="workspace_id required for workspace invite")

        workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace_name = workspace.name

    # Create invite
    invite = Invite(
        token=Invite.generate_token(),
        type=InviteType(request.type.value),
        email=request.email,
        workspace_id=request.workspace_id,
        created_by_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=request.expires_in_hours)
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteResponse(
        id=invite.id,
        token=invite.token,
        type=InviteTypeEnum(invite.type.value),
        email=invite.email,
        workspace_id=invite.workspace_id,
        workspace_name=workspace_name,
        created_by_id=invite.created_by_id,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        used_at=invite.used_at,
        used_by_id=invite.used_by_id,
        is_valid=invite.is_valid
    )


@router.get("/invites", response_model=List[InviteResponse])
def list_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all invites (admin only)"""
    invites = db.query(Invite).order_by(Invite.created_at.desc()).all()

    result = []
    for invite in invites:
        workspace_name = None
        if invite.workspace_id:
            workspace = db.query(Workspace).filter(Workspace.id == invite.workspace_id).first()
            workspace_name = workspace.name if workspace else None

        result.append(InviteResponse(
            id=invite.id,
            token=invite.token,
            type=InviteTypeEnum(invite.type.value),
            email=invite.email,
            workspace_id=invite.workspace_id,
            workspace_name=workspace_name,
            created_by_id=invite.created_by_id,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            used_at=invite.used_at,
            used_by_id=invite.used_by_id,
            is_valid=invite.is_valid
        ))

    return result


@router.delete("/invites/{invite_id}")
def delete_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete an invite (admin only)"""
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.is_used:
        raise HTTPException(status_code=400, detail="Cannot delete used invite")

    db.delete(invite)
    db.commit()
    return {"message": "Invite deleted"}


@router.get("/invite/{token}", response_model=InviteValidateResponse)
def validate_invite(
    token: str,
    db: Session = Depends(get_db)
):
    """Validate an invite token (public endpoint)"""
    invite = db.query(Invite).filter(Invite.token == token).first()

    if not invite:
        return InviteValidateResponse(valid=False, error="Invalid invite token")

    if invite.is_used:
        return InviteValidateResponse(valid=False, error="Invite has already been used")

    if invite.is_expired:
        return InviteValidateResponse(valid=False, error="Invite has expired")

    workspace_name = None
    if invite.workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == invite.workspace_id).first()
        workspace_name = workspace.name if workspace else None

    return InviteValidateResponse(
        valid=True,
        type=InviteTypeEnum(invite.type.value),
        email=invite.email,
        workspace_name=workspace_name,
        expires_at=invite.expires_at
    )


# ============== Workspace Endpoints ==============

workspaces_router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def get_user_workspaces(db: Session, user_id: int) -> List[Workspace]:
    """Get all workspaces user is a member of"""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    return db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).order_by(Workspace.name).all()


@workspaces_router.get("", response_model=List[WorkspaceResponse])
def list_my_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List workspaces the current user belongs to"""
    workspaces = get_user_workspaces(db, current_user.id)
    result = []
    for ws in workspaces:
        member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
        result.append(WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            created_at=ws.created_at,
            member_count=member_count,
            is_owner=ws.owner_id == current_user.id
        ))
    return result


@workspaces_router.get("/all", response_model=List[WorkspaceResponse])
def list_all_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all workspaces (admin only) - for invite creation"""
    workspaces = db.query(Workspace).order_by(Workspace.name).all()
    result = []
    for ws in workspaces:
        member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
        result.append(WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            created_at=ws.created_at,
            member_count=member_count,
            is_owner=ws.owner_id == current_user.id
        ))
    return result


@workspaces_router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    request: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new workspace"""
    if not current_user.can_create_workspace:
        raise HTTPException(status_code=403, detail="You don't have permission to create workspaces")

    workspace = Workspace(
        name=request.name,
        owner_id=current_user.id
    )
    db.add(workspace)
    db.flush()

    # Add creator as owner
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER.value
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at,
        member_count=1,
        is_owner=True
    )


@workspaces_router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get workspace details with members"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check if user is a member
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()

    if not membership and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="You don't have access to this workspace")

    # Get all members with user info
    members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
    member_responses = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        member_responses.append(WorkspaceMemberResponse(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                role=user.role,
                can_create_workspace=user.can_create_workspace,
                created_at=user.created_at
            ) if user else None
        ))

    return WorkspaceDetailResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at,
        members=member_responses,
        is_owner=workspace.owner_id == current_user.id
    )


@workspaces_router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    request: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update workspace name (owner only)"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if workspace.owner_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only workspace owner can update it")

    workspace.name = request.name
    db.commit()
    db.refresh(workspace)

    member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace.id).count()
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at,
        member_count=member_count,
        is_owner=workspace.owner_id == current_user.id
    )


@workspaces_router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete workspace (owner only)"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if workspace.owner_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only workspace owner can delete it")

    # Check if workspace has projects
    from app.models.project import Project
    project_count = db.query(Project).filter(Project.workspace_id == workspace_id).count()
    if project_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete workspace with {project_count} projects. Delete projects first.")

    # Delete members first
    db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).delete()
    db.delete(workspace)
    db.commit()

    return {"message": "Workspace deleted"}


@workspaces_router.delete("/{workspace_id}/members/{user_id}")
def remove_workspace_member(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from workspace (owner only, cannot remove owner)"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if workspace.owner_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only workspace owner can remove members")

    if user_id == workspace.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove workspace owner")

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in this workspace")

    db.delete(membership)
    db.commit()

    return {"message": "Member removed"}
