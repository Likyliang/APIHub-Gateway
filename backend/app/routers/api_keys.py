"""
API Keys Routes - Enhanced with batch creation, rate limits, and token system
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from ..database import get_db
from ..services.key_service import APIKeyService
from ..middleware.auth import get_current_active_user, get_admin_user
from ..models.user import User
from ..config import settings


router = APIRouter(prefix="/keys", tags=["API Keys"])

# HTTP client for fetching models
_http_client = None

def get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


# ===========================================
# Models Endpoint (JWT Auth)
# ===========================================

@router.get("/models")
async def list_available_models(
    current_user: User = Depends(get_current_active_user),
):
    """Get available models from upstream (for API key creation)."""
    try:
        client = get_http_client()
        headers = {}
        if settings.upstream_api_key:
            headers["Authorization"] = f"Bearer {settings.upstream_api_key}"

        response = await client.get(
            f"{settings.upstream_url}/v1/models",
            headers=headers,
        )

        if response.status_code == 200:
            data = response.json()
            # Extract model IDs from response
            models = []
            if "data" in data:
                for model in data["data"]:
                    if isinstance(model, dict) and "id" in model:
                        models.append(model["id"])
                    elif isinstance(model, str):
                        models.append(model)
            return {"models": sorted(models)}
        else:
            return {"models": [], "error": "Failed to fetch models from upstream"}
    except Exception as e:
        return {"models": [], "error": str(e)}


# ===========================================
# Request Models
# ===========================================

class APIKeyCreate(BaseModel):
    """Create a single API key."""
    name: str
    description: Optional[str] = None
    rate_limit: int = Field(default=60, ge=1, description="Requests per minute")
    rate_limit_day: Optional[int] = Field(default=None, ge=1, description="Requests per day (null = unlimited)")
    quota_limit: Optional[float] = Field(default=None, ge=0, description="Quota limit (null = use user quota)")
    token_limit: Optional[float] = Field(default=None, ge=0, description="Token limit (null = unlimited)")
    discount_rate: float = Field(default=1.0, gt=0, le=1.0, description="Discount rate (< 1.0 = discount)")
    allowed_models: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyBatchCreate(BaseModel):
    """Batch create API keys."""
    count: int = Field(ge=1, le=100, description="Number of keys to create (max 100)")
    name_prefix: str = Field(default="Key", description="Prefix for key names")
    description: Optional[str] = None
    rate_limit: int = Field(default=60, ge=1, description="Requests per minute")
    rate_limit_day: Optional[int] = Field(default=None, ge=1, description="Requests per day (null = unlimited)")
    quota_limit: Optional[float] = Field(default=None, ge=0, description="Quota limit per key")
    token_limit: Optional[float] = Field(default=None, ge=0, description="Token limit per key")
    discount_rate: float = Field(default=1.0, gt=0, le=1.0, description="Discount rate (< 1.0 = discount)")
    allowed_models: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyUpdate(BaseModel):
    """Update an API key."""
    name: Optional[str] = None
    description: Optional[str] = None
    rate_limit: Optional[int] = Field(default=None, ge=1)
    rate_limit_day: Optional[int] = Field(default=None, ge=1)
    quota_limit: Optional[float] = Field(default=None, ge=0)
    token_limit: Optional[float] = Field(default=None, ge=0)
    discount_rate: Optional[float] = Field(default=None, gt=0, le=1.0)
    allowed_models: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ===========================================
# Response Models
# ===========================================

class APIKeyResponse(BaseModel):
    """API key response (without plain key)."""
    id: int
    key: str  # Masked key for display
    name: str
    description: Optional[str]
    is_active: bool
    rate_limit: int
    rate_limit_day: Optional[int]
    quota_limit: Optional[float]
    quota_used: float
    token_limit: Optional[float]
    token_used: float
    discount_rate: float
    total_requests: int
    total_tokens: int
    total_cost: float
    batch_id: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(APIKeyResponse):
    """Response when creating a key (includes plain key)."""
    plain_key: str  # Only returned on creation


class APIKeyBatchResponse(BaseModel):
    """Response for batch creation."""
    batch_id: str
    count: int
    keys: List[APIKeyCreatedResponse]


# ===========================================
# Endpoints - User
# ===========================================

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
        rate_limit_day=key_data.rate_limit_day,
        quota_limit=key_data.quota_limit,
        token_limit=key_data.token_limit,
        discount_rate=key_data.discount_rate,
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
        rate_limit_day=api_key.rate_limit_day,
        quota_limit=api_key.quota_limit,
        quota_used=api_key.quota_used,
        token_limit=api_key.token_limit,
        token_used=api_key.token_used,
        discount_rate=api_key.discount_rate,
        total_requests=api_key.total_requests,
        total_tokens=api_key.total_tokens,
        total_cost=api_key.total_cost,
        batch_id=api_key.batch_id,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
    )


@router.post("/batch", response_model=APIKeyBatchResponse)
async def create_batch_keys(
    batch_data: APIKeyBatchCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch create API keys with the same settings."""
    key_service = APIKeyService(db)

    batch_id, results = await key_service.create_batch(
        user_id=current_user.id,
        count=batch_data.count,
        name_prefix=batch_data.name_prefix,
        description=batch_data.description,
        rate_limit=batch_data.rate_limit,
        rate_limit_day=batch_data.rate_limit_day,
        quota_limit=batch_data.quota_limit,
        token_limit=batch_data.token_limit,
        discount_rate=batch_data.discount_rate,
        allowed_models=batch_data.allowed_models,
        expires_at=batch_data.expires_at,
    )

    keys = []
    for api_key, plain_key in results:
        keys.append(APIKeyCreatedResponse(
            id=api_key.id,
            key=api_key.key,
            plain_key=plain_key,
            name=api_key.name,
            description=api_key.description,
            is_active=api_key.is_active,
            rate_limit=api_key.rate_limit,
            rate_limit_day=api_key.rate_limit_day,
            quota_limit=api_key.quota_limit,
            quota_used=api_key.quota_used,
            token_limit=api_key.token_limit,
            token_used=api_key.token_used,
            discount_rate=api_key.discount_rate,
            total_requests=api_key.total_requests,
            total_tokens=api_key.total_tokens,
            total_cost=api_key.total_cost,
            batch_id=api_key.batch_id,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
        ))

    return APIKeyBatchResponse(
        batch_id=batch_id,
        count=len(keys),
        keys=keys,
    )


@router.get("/batch/{batch_id}", response_model=List[APIKeyResponse])
async def get_batch_keys(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all API keys in a batch."""
    key_service = APIKeyService(db)
    keys = await key_service.get_keys_by_batch(batch_id)

    # Filter to only show user's own keys
    user_keys = [k for k in keys if k.user_id == current_user.id]
    if not user_keys and keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Batch belongs to another user",
        )

    return user_keys


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


@router.post("/{key_id}/reset-usage", response_model=APIKeyResponse)
async def reset_key_usage(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset usage statistics for an API key."""
    key_service = APIKeyService(db)

    # Verify ownership
    api_key = await key_service.get_key_by_id(key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key = await key_service.reset_key_usage(key_id)
    return api_key


# ===========================================
# Admin Endpoints
# ===========================================

@router.get("/admin/all", response_model=List[APIKeyResponse])
async def admin_list_all_keys(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all API keys in the system."""
    key_service = APIKeyService(db)
    keys = await key_service.get_all_keys(skip=skip, limit=limit)
    return keys


@router.get("/admin/user/{user_id}", response_model=List[APIKeyResponse])
async def admin_list_user_keys(
    user_id: int,
    include_inactive: bool = False,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all API keys for a specific user."""
    key_service = APIKeyService(db)
    keys = await key_service.get_keys_by_user(user_id, include_inactive=include_inactive)
    return keys


@router.post("/admin/user/{user_id}", response_model=APIKeyCreatedResponse)
async def admin_create_key_for_user(
    user_id: int,
    key_data: APIKeyCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Create an API key for a specific user."""
    key_service = APIKeyService(db)

    api_key, plain_key = await key_service.create_key(
        user_id=user_id,
        name=key_data.name,
        description=key_data.description,
        rate_limit=key_data.rate_limit,
        rate_limit_day=key_data.rate_limit_day,
        quota_limit=key_data.quota_limit,
        token_limit=key_data.token_limit,
        discount_rate=key_data.discount_rate,
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
        rate_limit_day=api_key.rate_limit_day,
        quota_limit=api_key.quota_limit,
        quota_used=api_key.quota_used,
        token_limit=api_key.token_limit,
        token_used=api_key.token_used,
        discount_rate=api_key.discount_rate,
        total_requests=api_key.total_requests,
        total_tokens=api_key.total_tokens,
        total_cost=api_key.total_cost,
        batch_id=api_key.batch_id,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
    )


@router.post("/admin/user/{user_id}/batch", response_model=APIKeyBatchResponse)
async def admin_create_batch_for_user(
    user_id: int,
    batch_data: APIKeyBatchCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Batch create API keys for a specific user."""
    key_service = APIKeyService(db)

    batch_id, results = await key_service.create_batch(
        user_id=user_id,
        count=batch_data.count,
        name_prefix=batch_data.name_prefix,
        description=batch_data.description,
        rate_limit=batch_data.rate_limit,
        rate_limit_day=batch_data.rate_limit_day,
        quota_limit=batch_data.quota_limit,
        token_limit=batch_data.token_limit,
        discount_rate=batch_data.discount_rate,
        allowed_models=batch_data.allowed_models,
        expires_at=batch_data.expires_at,
    )

    keys = []
    for api_key, plain_key in results:
        keys.append(APIKeyCreatedResponse(
            id=api_key.id,
            key=api_key.key,
            plain_key=plain_key,
            name=api_key.name,
            description=api_key.description,
            is_active=api_key.is_active,
            rate_limit=api_key.rate_limit,
            rate_limit_day=api_key.rate_limit_day,
            quota_limit=api_key.quota_limit,
            quota_used=api_key.quota_used,
            token_limit=api_key.token_limit,
            token_used=api_key.token_used,
            discount_rate=api_key.discount_rate,
            total_requests=api_key.total_requests,
            total_tokens=api_key.total_tokens,
            total_cost=api_key.total_cost,
            batch_id=api_key.batch_id,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
        ))

    return APIKeyBatchResponse(
        batch_id=batch_id,
        count=len(keys),
        keys=keys,
    )


@router.put("/admin/{key_id}", response_model=APIKeyResponse)
async def admin_update_key(
    key_id: int,
    key_data: APIKeyUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Update any API key."""
    key_service = APIKeyService(db)

    api_key = await key_service.get_key_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Admin can update any key
    updates = key_data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if hasattr(api_key, key) and key not in ("key", "key_hash", "user_id"):
            setattr(api_key, key, value)

    await db.flush()
    await db.refresh(api_key)

    return api_key


@router.delete("/admin/{key_id}")
async def admin_delete_key(
    key_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Delete any API key."""
    key_service = APIKeyService(db)

    api_key = await key_service.get_key_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    return {"message": "API key deleted"}


@router.post("/admin/{key_id}/reset-usage", response_model=APIKeyResponse)
async def admin_reset_key_usage(
    key_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Reset usage statistics for any API key."""
    key_service = APIKeyService(db)
    api_key = await key_service.reset_key_usage(key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return api_key
