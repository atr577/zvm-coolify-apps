from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.db.base import get_db
from app.models.user import User, SocialAccount
from app.schemas.auth import SocialAccountResponse, SocialAccountCreate
from app.core.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=List[SocialAccountResponse])
def list_social_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список всех социальных аккаунтов пользователя"""
    accounts = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id
    ).all()
    return accounts


@router.get("/{account_id}", response_model=SocialAccountResponse)
def get_social_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить конкретный социальный аккаунт"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found"
        )

    return account


@router.post("/", response_model=SocialAccountResponse, status_code=status.HTTP_201_CREATED)
def create_social_account(
    request: SocialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавить новый социальный аккаунт (используется OAuth callback)"""
    # Проверить, не существует ли уже этот аккаунт
    existing = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == request.platform,
        SocialAccount.platform_user_id == request.platform_user_id
    ).first()

    if existing:
        # Обновляем токены если аккаунт уже существует
        existing.access_token = request.access_token
        existing.refresh_token = request.refresh_token
        existing.username = request.username
        existing.display_name = request.display_name
        existing.profile_picture = request.profile_picture
        existing.platform_data = request.platform_data
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    # Создаем новый аккаунт
    new_account = SocialAccount(
        user_id=current_user.id,
        platform=request.platform,
        access_token=request.access_token,
        refresh_token=request.refresh_token,
        platform_user_id=request.platform_user_id,
        username=request.username,
        display_name=request.display_name,
        profile_picture=request.profile_picture,
        platform_data=request.platform_data,
        is_active=True
    )

    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


@router.patch("/{account_id}", response_model=SocialAccountResponse)
def update_social_account(
    account_id: int,
    access_token: str = None,
    refresh_token: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить социальный аккаунт (например, refresh token)"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found"
        )

    if access_token is not None:
        account.access_token = access_token
    if refresh_token is not None:
        account.refresh_token = refresh_token
    if is_active is not None:
        account.is_active = is_active

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_social_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отключить/удалить социальный аккаунт"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found"
        )

    db.delete(account)
    db.commit()
    return {"message": "Social account deleted successfully"}


@router.get("/platform/{platform}", response_model=List[SocialAccountResponse])
def list_accounts_by_platform(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить все аккаунты пользователя для конкретной платформы"""
    accounts = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == platform
    ).all()
    return accounts
