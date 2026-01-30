"""
User Management Routes (Admin)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.user_service import UserService
from ..services.key_service import APIKeyService
from ..middleware.auth import get_admin_user
from ..models.user import User


router = APIRouter(prefix="/users", tags=["User Management"])


class UserCreateAdmin(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: bool = False
    quota_limit: float = 100.0


class UserUpdateAdmin(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    quota_limit: Optional[float] = None
    quota_used: Optional[float] = None


class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    quota_limit: float
    quota_used: float
    created_at: str
    last_login: Optional[str]
    api_key_count: int = 0

    class Config:
        from_attributes = True


@router.get("", response_model=List[UserDetailResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    user_service = UserService(db)
    key_service = APIKeyService(db)
    users = await user_service.get_all_users(skip=skip, limit=limit)

    result = []
    for user in users:
        keys = await key_service.get_keys_by_user(user.id, include_inactive=True)
        result.append(
            UserDetailResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                quota_limit=user.quota_limit,
                quota_used=user.quota_used,
                created_at=user.created_at.isoformat() if user.created_at else "",
                last_login=user.last_login.isoformat() if user.last_login else None,
                api_key_count=len(keys),
            )
        )

    return result


@router.post("", response_model=UserDetailResponse)
async def create_user(
    user_data: UserCreateAdmin,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    user_service = UserService(db)

    # Check if username exists
    existing = await user_service.get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    existing = await user_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = await user_service.create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        is_admin=user_data.is_admin,
        quota_limit=user_data.quota_limit,
    )

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        quota_limit=user.quota_limit,
        quota_used=user.quota_used,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=None,
        api_key_count=0,
    )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user (admin only)."""
    user_service = UserService(db)
    key_service = APIKeyService(db)

    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    keys = await key_service.get_keys_by_user(user.id, include_inactive=True)

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        quota_limit=user.quota_limit,
        quota_used=user.quota_used,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
        api_key_count=len(keys),
    )


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateAdmin,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user (admin only)."""
    user_service = UserService(db)
    key_service = APIKeyService(db)

    updates = user_data.model_dump(exclude_unset=True)
    user = await user_service.update_user(user_id, **updates)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    keys = await key_service.get_keys_by_user(user.id, include_inactive=True)

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        quota_limit=user.quota_limit,
        quota_used=user.quota_used,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
        api_key_count=len(keys),
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only)."""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    user_service = UserService(db)
    success = await user_service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"message": "User deleted"}


@router.post("/{user_id}/reset-quota")
async def reset_user_quota(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset a user's quota (admin only)."""
    user_service = UserService(db)
    user = await user_service.reset_quota(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"message": "Quota reset", "quota_used": user.quota_used}
