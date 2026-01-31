"""
Authentication Routes
"""
import math
from datetime import datetime, timedelta
from typing import Optional, Dict
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_serializer
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.user_service import UserService
from ..utils.auth import create_access_token
from ..config import settings
from ..middleware.auth import get_current_active_user
from ..models.user import User


router = APIRouter(prefix="/auth", tags=["Authentication"])

# Login attempt tracking for brute-force protection
login_attempts: Dict[str, list] = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes in seconds


def check_login_rate_limit(identifier: str) -> None:
    """Check if login is rate limited due to too many failed attempts."""
    now = datetime.now()
    # Clean up old attempts (older than lockout duration)
    login_attempts[identifier] = [
        t for t in login_attempts[identifier]
        if (now - t).total_seconds() < LOCKOUT_DURATION
    ]

    if len(login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        remaining = LOCKOUT_DURATION - (now - login_attempts[identifier][0]).total_seconds()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {int(remaining)} seconds.",
        )


def record_failed_login(identifier: str) -> None:
    """Record a failed login attempt."""
    login_attempts[identifier].append(datetime.now())


def clear_login_attempts(identifier: str) -> None:
    """Clear login attempts after successful login."""
    if identifier in login_attempts:
        del login_attempts[identifier]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    quota_limit: Optional[float]
    quota_used: float

    class Config:
        from_attributes = True

    @field_serializer('quota_limit')
    def serialize_quota_limit(self, value: float) -> Optional[float]:
        if value is None or math.isinf(value):
            return None
        return value


class UserUpdate(BaseModel):
    """Update user profile."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
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
    )

    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and get access token."""
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{form_data.username}"

    # Check rate limit
    check_login_rate_limit(identifier)

    user_service = UserService(db)
    user = await user_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        # Record failed attempt
        record_failed_login(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clear login attempts on success
    clear_login_attempts(identifier)

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return Token(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user info."""
    quota_limit = current_user.quota_limit
    if quota_limit is not None and math.isinf(quota_limit):
        quota_limit = None

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        quota_limit=quota_limit,
        quota_used=current_user.quota_used,
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user info (including username)."""
    user_service = UserService(db)

    updates = {}

    # Handle username update
    if user_data.username and user_data.username != current_user.username:
        # Check if new username is taken
        existing = await user_service.get_user_by_username(user_data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        updates["username"] = user_data.username

    # Handle email update
    if user_data.email and user_data.email != current_user.email:
        existing = await user_service.get_user_by_email(user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        updates["email"] = user_data.email

    # Handle password update
    if user_data.password:
        updates["password"] = user_data.password

    user = current_user
    if updates:
        user = await user_service.update_user(current_user.id, **updates)

    quota_limit = user.quota_limit
    if quota_limit is not None and math.isinf(quota_limit):
        quota_limit = None

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        quota_limit=quota_limit,
        quota_used=user.quota_used,
    )
