"""
API Keys Routes
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.key_service import APIKeyService
from ..middleware.auth import get_current_active_user
from ..models.user import User


router = APIRouter(prefix="/keys", tags=["API Keys"])


class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rate_limit: int = 60
    quota_limit: Optional[float] = None
    allowed_models: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rate_limit: Optional[int] = None
    quota_limit: Optional[float] = None
    allowed_models: Optional[List[str]] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    id: int
    key: str
    name: str
    description: Optional[str]
    is_active: bool
    rate_limit: int
    quota_limit: Optional[float]
    quota_used: float
    total_requests: int
    total_tokens: int
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(APIKeyResponse):
    plain_key: str  # Only returned on creation


@router.post("", response_model=APIKeyCreatedResponse)
async def create_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key."""
    key_service = APIKeyService(db)

    api_key, plain_key = await key_service.create_key(
        user_id=current_user.id,
        name=key_data.name,
        description=key_data.description,
        rate_limit=key_data.rate_limit,
        quota_limit=key_data.quota_limit,
        allowed_models=key_data.allowed_models,
        expires_at=key_data.expires_at,
    )

    return APIKeyCreatedResponse(
        id=api_key.id,
        key=api_key.key,
        plain_key=plain_key,
        name=api_key.name,
        description=api_key.description,
        is_active=api_key.is_active,
        rate_limit=api_key.rate_limit,
        quota_limit=api_key.quota_limit,
        quota_used=api_key.quota_used,
        total_requests=api_key.total_requests,
        total_tokens=api_key.total_tokens,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
    )


@router.get("", response_model=List[APIKeyResponse])
async def list_keys(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for current user."""
    key_service = APIKeyService(db)
    keys = await key_service.get_keys_by_user(
        current_user.id, include_inactive=include_inactive
    )
    return keys


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific API key."""
    key_service = APIKeyService(db)
    api_key = await key_service.get_key_by_id(key_id)

    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return api_key


@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_key(
    key_id: int,
    key_data: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an API key."""
    key_service = APIKeyService(db)

    updates = key_data.model_dump(exclude_unset=True)
    api_key = await key_service.update_key(key_id, current_user.id, **updates)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return api_key


@router.delete("/{key_id}")
async def delete_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an API key."""
    key_service = APIKeyService(db)
    success = await key_service.delete_key(key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return {"message": "API key deleted"}


@router.post("/{key_id}/deactivate")
async def deactivate_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an API key."""
    key_service = APIKeyService(db)
    success = await key_service.deactivate_key(key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return {"message": "API key deactivated"}
