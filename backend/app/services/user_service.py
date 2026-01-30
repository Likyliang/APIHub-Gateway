"""
User Service - Business logic for user management
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.user import User
from ..utils.auth import get_password_hash, verify_password


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False,
        quota_limit: float = 100.0,
    ) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin,
            quota_limit=quota_limit,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        return user

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_user(
        self,
        user_id: int,
        **kwargs,
    ) -> Optional[User]:
        """Update user attributes."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        # Handle password specially
        if "password" in kwargs:
            kwargs["hashed_password"] = get_password_hash(kwargs.pop("password"))

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        await self.db.delete(user)
        return True

    async def update_quota_used(self, user_id: int, amount: float) -> Optional[User]:
        """Update user's quota usage."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        user.quota_used += amount
        return user

    async def reset_quota(self, user_id: int) -> Optional[User]:
        """Reset user's quota usage."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        user.quota_used = 0.0
        user.quota_reset_date = datetime.now(timezone.utc)
        return user

    async def check_quota(self, user_id: int) -> tuple[bool, float, float]:
        """Check if user has remaining quota. Returns (has_quota, used, limit)."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, 0.0, 0.0
        return user.quota_used < user.quota_limit, user.quota_used, user.quota_limit
