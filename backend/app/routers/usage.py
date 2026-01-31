"""
Usage Statistics Routes
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.usage_service import UsageService
from ..middleware.auth import get_current_active_user, get_admin_user
from ..models.user import User


router = APIRouter(prefix="/usage", tags=["Usage Statistics"])


class UsageRecordResponse(BaseModel):
    id: int
    request_id: str
    endpoint: str
    method: str
    model: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    status_code: Optional[int]
    response_time_ms: Optional[int]
    is_streaming: bool
    is_success: bool
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: float
    avg_response_time_ms: float
    success_count: int
    error_count: int
    success_rate: float
    period_start: str
    period_end: str


class ModelBreakdownResponse(BaseModel):
    model: str
    request_count: int
    total_tokens: int
    total_cost: float


class DailyUsageResponse(BaseModel):
    date: str
    request_count: int
    total_tokens: int
    total_cost: float


@router.get("/records", response_model=List[UsageRecordResponse])
async def get_usage_records(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage records for current user."""
    usage_service = UsageService(db)
    records = await usage_service.get_user_usage(
        current_user.id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return records


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated usage statistics for current user."""
    usage_service = UsageService(db)
    stats = await usage_service.get_user_stats(
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return stats


@router.get("/models", response_model=List[ModelBreakdownResponse])
async def get_model_breakdown(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage breakdown by model for current user."""
    usage_service = UsageService(db)
    breakdown = await usage_service.get_model_breakdown(
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return breakdown


@router.get("/daily", response_model=List[DailyUsageResponse])
async def get_daily_usage(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily usage for the past N days."""
    usage_service = UsageService(db)
    daily = await usage_service.get_daily_usage(current_user.id, days=days)
    return daily


@router.get("/quota")
async def get_quota_status(
    current_user: User = Depends(get_current_active_user),
):
    """Get current quota status."""
    import math

    quota_limit = current_user.quota_limit
    quota_used = current_user.quota_used

    # Handle infinity for JSON serialization
    if math.isinf(quota_limit):
        quota_remaining = float("inf")
        quota_percentage = 0
        quota_limit_display = None  # null means unlimited
    else:
        quota_remaining = max(0, quota_limit - quota_used)
        quota_percentage = (quota_used / quota_limit * 100) if quota_limit > 0 else 0
        quota_limit_display = quota_limit

    return {
        "quota_limit": quota_limit_display,
        "quota_used": quota_used,
        "quota_remaining": quota_remaining if not math.isinf(quota_remaining) else None,
        "quota_percentage": quota_percentage,
        "is_unlimited": math.isinf(current_user.quota_limit),
    }


# Admin endpoints
@router.get("/admin/global", response_model=UsageStatsResponse)
async def get_global_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get global usage statistics (admin only)."""
    usage_service = UsageService(db)
    stats = await usage_service.get_global_stats(
        start_date=start_date,
        end_date=end_date,
    )
    return stats
