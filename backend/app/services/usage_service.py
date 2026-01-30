"""
Usage Service - Business logic for usage tracking and statistics
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.usage import UsageRecord, UsageStats
from ..utils.auth import generate_api_key


def generate_request_id() -> str:
    """Generate a unique request ID."""
    import secrets
    return secrets.token_hex(16)


class UsageService:
    """Service for usage tracking and statistics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_usage(
        self,
        user_id: int,
        api_key_id: int,
        endpoint: str,
        method: str,
        model: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        is_streaming: bool = False,
        is_success: bool = True,
        error_message: Optional[str] = None,
    ) -> UsageRecord:
        """Record a single API usage event."""
        record = UsageRecord(
            request_id=generate_request_id(),
            user_id=user_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            status_code=status_code,
            response_time_ms=response_time_ms,
            is_streaming=is_streaming,
            is_success=is_success,
            error_message=error_message,
        )

        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_user_usage(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UsageRecord]:
        """Get usage records for a user."""
        query = select(UsageRecord).where(UsageRecord.user_id == user_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        query = query.order_by(UsageRecord.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_key_usage(
        self,
        api_key_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UsageRecord]:
        """Get usage records for an API key."""
        query = select(UsageRecord).where(UsageRecord.api_key_id == api_key_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        query = query.order_by(UsageRecord.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_stats(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated statistics for a user."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        query = select(
            func.count(UsageRecord.id).label("total_requests"),
            func.sum(UsageRecord.prompt_tokens).label("total_prompt_tokens"),
            func.sum(UsageRecord.completion_tokens).label("total_completion_tokens"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost).label("total_cost"),
            func.avg(UsageRecord.response_time_ms).label("avg_response_time"),
            func.count(UsageRecord.id).filter(UsageRecord.is_success == True).label("success_count"),
            func.count(UsageRecord.id).filter(UsageRecord.is_success == False).label("error_count"),
        ).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.created_at >= start_date,
                UsageRecord.created_at <= end_date,
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_requests": row.total_requests or 0,
            "total_prompt_tokens": row.total_prompt_tokens or 0,
            "total_completion_tokens": row.total_completion_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost": float(row.total_cost or 0),
            "avg_response_time_ms": float(row.avg_response_time or 0),
            "success_count": row.success_count or 0,
            "error_count": row.error_count or 0,
            "success_rate": (
                (row.success_count / row.total_requests * 100)
                if row.total_requests
                else 100.0
            ),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }

    async def get_model_breakdown(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by model for a user."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        query = select(
            UsageRecord.model,
            func.count(UsageRecord.id).label("request_count"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost).label("total_cost"),
        ).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.created_at >= start_date,
                UsageRecord.created_at <= end_date,
                UsageRecord.model.isnot(None),
            )
        ).group_by(UsageRecord.model).order_by(func.count(UsageRecord.id).desc())

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "model": row.model,
                "request_count": row.request_count,
                "total_tokens": row.total_tokens or 0,
                "total_cost": float(row.total_cost or 0),
            }
            for row in rows
        ]

    async def get_daily_usage(
        self,
        user_id: int,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily usage for the past N days."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        query = select(
            func.date(UsageRecord.created_at).label("date"),
            func.count(UsageRecord.id).label("request_count"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost).label("total_cost"),
        ).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.created_at >= start_date,
                UsageRecord.created_at <= end_date,
            )
        ).group_by(func.date(UsageRecord.created_at)).order_by(func.date(UsageRecord.created_at))

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "date": str(row.date),
                "request_count": row.request_count,
                "total_tokens": row.total_tokens or 0,
                "total_cost": float(row.total_cost or 0),
            }
            for row in rows
        ]

    async def get_global_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get global usage statistics (admin only)."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        query = select(
            func.count(UsageRecord.id).label("total_requests"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost).label("total_cost"),
            func.count(func.distinct(UsageRecord.user_id)).label("unique_users"),
            func.count(func.distinct(UsageRecord.api_key_id)).label("unique_keys"),
        ).where(
            and_(
                UsageRecord.created_at >= start_date,
                UsageRecord.created_at <= end_date,
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_requests": row.total_requests or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost": float(row.total_cost or 0),
            "unique_users": row.unique_users or 0,
            "unique_keys": row.unique_keys or 0,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
