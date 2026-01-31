"""
API Key Service - Business logic for API key management
"""
import json
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.api_key import APIKey
from ..utils.auth import generate_api_key, hash_api_key


class APIKeyService:
    """Service for API key management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_key(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        rate_limit: int = 60,
        rate_limit_day: Optional[int] = None,
        quota_limit: Optional[float] = None,
        token_limit: Optional[float] = None,
        discount_rate: float = 1.0,
        allowed_models: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        batch_id: Optional[str] = None,
    ) -> Tuple[APIKey, str]:
        """Create a new API key. Returns (key_model, plain_key)."""
        # Generate the key
        plain_key = generate_api_key()
        key_hash = hash_api_key(plain_key)

        api_key = APIKey(
            key=plain_key[:20] + "..." + plain_key[-8:],  # Masked for display
            key_hash=key_hash,
            name=name,
            description=description,
            user_id=user_id,
            rate_limit=rate_limit,
            rate_limit_day=rate_limit_day,
            quota_limit=quota_limit,
            token_limit=token_limit,
            discount_rate=discount_rate,
            allowed_models=json.dumps(allowed_models or []),
            expires_at=expires_at,
            batch_id=batch_id,
        )

        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)

        return api_key, plain_key

    async def create_batch(
        self,
        user_id: int,
        count: int,
        name_prefix: str = "Key",
        description: Optional[str] = None,
        rate_limit: int = 60,
        rate_limit_day: Optional[int] = None,
        quota_limit: Optional[float] = None,
        token_limit: Optional[float] = None,
        discount_rate: float = 1.0,
        allowed_models: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[str, List[Tuple[APIKey, str]]]:
        """
        Batch create API keys.
        Returns (batch_id, list of (key_model, plain_key))
        """
        batch_id = f"batch_{secrets.token_hex(8)}"
        results = []

        for i in range(count):
            name = f"{name_prefix}_{i + 1}"
            api_key, plain_key = await self.create_key(
                user_id=user_id,
                name=name,
                description=description,
                rate_limit=rate_limit,
                rate_limit_day=rate_limit_day,
                quota_limit=quota_limit,
                token_limit=token_limit,
                discount_rate=discount_rate,
                allowed_models=allowed_models,
                expires_at=expires_at,
                batch_id=batch_id,
            )
            results.append((api_key, plain_key))

        return batch_id, results

    async def get_keys_by_batch(self, batch_id: str) -> List[APIKey]:
        """Get all API keys in a batch."""
        result = await self.db.execute(
            select(APIKey).where(APIKey.batch_id == batch_id).order_by(APIKey.id)
        )
        return list(result.scalars().all())

    async def get_key_by_id(self, key_id: int) -> Optional[APIKey]:
        """Get API key by ID."""
        result = await self.db.execute(select(APIKey).where(APIKey.id == key_id))
        return result.scalar_one_or_none()

    async def get_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        result = await self.db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def validate_key(self, plain_key: str) -> Optional[APIKey]:
        """Validate an API key and return the key model if valid."""
        key_hash = hash_api_key(plain_key)
        api_key = await self.get_key_by_hash(key_hash)

        if not api_key:
            return None

        # Check if key is active
        if not api_key.is_active:
            return None

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None

        # Check token limit
        if api_key.token_limit is not None and api_key.token_used >= api_key.token_limit:
            return None

        # Check quota limit
        if api_key.quota_limit is not None and api_key.quota_used >= api_key.quota_limit:
            return None

        # Update last used
        api_key.last_used_at = datetime.now(timezone.utc)

        return api_key

    async def get_keys_by_user(
        self, user_id: int, include_inactive: bool = False
    ) -> List[APIKey]:
        """Get all API keys for a user."""
        query = select(APIKey).where(APIKey.user_id == user_id)
        if not include_inactive:
            query = query.where(APIKey.is_active == True)
        query = query.order_by(APIKey.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_key(self, key_id: int, user_id: int, **kwargs) -> Optional[APIKey]:
        """Update API key attributes."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key or api_key.user_id != user_id:
            return None

        # Handle allowed_models specially
        if "allowed_models" in kwargs:
            kwargs["allowed_models"] = json.dumps(kwargs["allowed_models"])

        for key, value in kwargs.items():
            if hasattr(api_key, key) and key not in ("key", "key_hash", "user_id"):
                setattr(api_key, key, value)

        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key

    async def deactivate_key(self, key_id: int, user_id: int) -> bool:
        """Deactivate an API key."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key or api_key.user_id != user_id:
            return False
        api_key.is_active = False
        return True

    async def delete_key(self, key_id: int, user_id: int) -> bool:
        """Delete an API key."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key or api_key.user_id != user_id:
            return False
        await self.db.delete(api_key)
        return True

    async def increment_usage(
        self,
        key_id: int,
        tokens: int = 0,
        cost: float = 0.0,
        apply_discount: bool = True,
    ) -> Optional[APIKey]:
        """Increment usage statistics for an API key."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key:
            return None

        # Apply discount if applicable
        actual_cost = cost
        if apply_discount and api_key.discount_rate < 1.0:
            actual_cost = cost * api_key.discount_rate

        api_key.total_requests += 1
        api_key.total_tokens += tokens
        api_key.token_used += tokens
        api_key.quota_used += actual_cost
        api_key.total_cost += actual_cost

        return api_key

    async def check_quota(self, key_id: int) -> Tuple[bool, float, Optional[float]]:
        """Check if API key has remaining quota. Returns (has_quota, used, limit)."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key:
            return False, 0.0, None

        if api_key.quota_limit is None:
            # No per-key limit, defer to user limit
            return True, api_key.quota_used, None

        return api_key.quota_used < api_key.quota_limit, api_key.quota_used, api_key.quota_limit

    async def check_token_limit(self, key_id: int) -> Tuple[bool, float, Optional[float]]:
        """Check if API key has remaining token limit. Returns (has_tokens, used, limit)."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key:
            return False, 0.0, None

        if api_key.token_limit is None:
            return True, api_key.token_used, None

        return api_key.token_used < api_key.token_limit, api_key.token_used, api_key.token_limit

    async def check_rate_limit_day(self, key_id: int, current_day_requests: int) -> Tuple[bool, int, Optional[int]]:
        """Check daily rate limit. Returns (within_limit, current_count, limit)."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key:
            return False, 0, None

        if api_key.rate_limit_day is None:
            return True, current_day_requests, None

        return current_day_requests < api_key.rate_limit_day, current_day_requests, api_key.rate_limit_day

    async def check_model_access(self, key_id: int, model: str) -> bool:
        """Check if API key has access to a specific model."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key:
            return False

        allowed_models = json.loads(api_key.allowed_models or "[]")
        if not allowed_models:
            # Empty list means all models allowed
            return True

        return model in allowed_models

    async def get_all_keys(self, skip: int = 0, limit: int = 100) -> List[APIKey]:
        """Get all API keys (admin only)."""
        result = await self.db.execute(
            select(APIKey).offset(skip).limit(limit).order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def reset_key_usage(self, key_id: int) -> Optional[APIKey]:
        """Reset usage statistics for an API key."""
        api_key = await self.get_key_by_id(key_id)
        if not api_key:
            return None

        api_key.quota_used = 0.0
        api_key.token_used = 0.0
        api_key.total_requests = 0
        api_key.total_tokens = 0

        return api_key
