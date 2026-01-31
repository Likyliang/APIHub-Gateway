"""
Token Routes - API for token/credit system management
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.token_service import TokenService
from ..middleware.auth import get_current_active_user, get_admin_user
from ..models.user import User


router = APIRouter(prefix="/tokens", tags=["Tokens"])


# ===========================================
# Request Models
# ===========================================

class RechargeRequest(BaseModel):
    """Recharge tokens to user balance."""
    amount: float = Field(gt=0, description="Amount to recharge")
    order_no: Optional[str] = Field(default=None, description="Payment order number")
    description: Optional[str] = None


class ConsumeRequest(BaseModel):
    """Consume tokens from user balance."""
    amount: float = Field(gt=0, description="Amount to consume")
    api_key_id: Optional[int] = Field(default=None, description="Related API key ID")
    description: Optional[str] = None
    apply_discount: bool = Field(default=True, description="Apply user discount rate")


class RefundRequest(BaseModel):
    """Refund tokens to user balance."""
    amount: float = Field(gt=0, description="Amount to refund")
    order_no: Optional[str] = Field(default=None, description="Related order number")
    description: Optional[str] = None


class AdjustRequest(BaseModel):
    """Adjust user balance (admin only)."""
    amount: float = Field(description="Amount to adjust (positive = add, negative = deduct)")
    description: Optional[str] = None


class SetDiscountRequest(BaseModel):
    """Set user discount rate."""
    discount_rate: float = Field(gt=0, le=1.0, description="Discount rate (< 1.0 = discount)")


class CheckBalanceRequest(BaseModel):
    """Check balance request."""
    amount: float = Field(gt=0, description="Amount to check")


# ===========================================
# Response Models
# ===========================================

class TransactionResponse(BaseModel):
    """Token transaction record."""
    id: int
    user_id: int
    amount: float
    balance_before: float
    balance_after: float
    transaction_type: str
    description: Optional[str]
    order_no: Optional[str]
    api_key_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    """User balance info."""
    balance: float
    total_recharged: float
    total_consumed: float
    discount_rate: float
    discount_percent: int


class OperationResponse(BaseModel):
    """Operation result."""
    success: bool
    new_balance: float
    transaction: Optional[TransactionResponse] = None
    message: Optional[str] = None


class CheckBalanceResponse(BaseModel):
    """Balance check result."""
    has_enough: bool
    current_balance: float
    required_amount: float
    actual_amount: float


# ===========================================
# User Endpoints
# ===========================================

@router.get("/balance", response_model=BalanceResponse)
async def get_my_balance(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's token balance and stats."""
    token_service = TokenService(db)
    stats = await token_service.get_user_stats(current_user.id)
    return BalanceResponse(**stats)


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_my_transactions(
    transaction_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's transaction history."""
    token_service = TokenService(db)
    transactions = await token_service.get_transactions(
        user_id=current_user.id,
        transaction_type=transaction_type,
        skip=skip,
        limit=limit,
    )
    return transactions


@router.post("/check", response_model=CheckBalanceResponse)
async def check_balance(
    request_data: CheckBalanceRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if user has enough balance for an amount."""
    token_service = TokenService(db)
    has_enough, current_balance = await token_service.check_balance(
        user_id=current_user.id,
        amount=request_data.amount,
    )

    actual_amount = request_data.amount
    if current_user.discount_rate < 1.0:
        actual_amount = request_data.amount * current_user.discount_rate

    return CheckBalanceResponse(
        has_enough=has_enough,
        current_balance=current_balance,
        required_amount=request_data.amount,
        actual_amount=actual_amount,
    )


# ===========================================
# Payment Integration Endpoints
# ===========================================

@router.post("/recharge/callback", response_model=OperationResponse)
async def recharge_callback(
    user_id: int,
    request_data: RechargeRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Recharge tokens to a user's balance (payment callback)."""
    token_service = TokenService(db)

    success, new_balance, transaction = await token_service.recharge(
        user_id=user_id,
        amount=request_data.amount,
        order_no=request_data.order_no,
        description=request_data.description,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to recharge tokens. User may not exist.",
        )

    tx_response = None
    if transaction:
        tx_response = TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            transaction_type=transaction.transaction_type,
            description=transaction.description,
            order_no=transaction.order_no,
            api_key_id=transaction.api_key_id,
            created_at=transaction.created_at,
        )

    return OperationResponse(
        success=True,
        new_balance=new_balance,
        transaction=tx_response,
        message="Tokens recharged successfully",
    )


# ===========================================
# Admin Endpoints
# ===========================================

@router.get("/admin/user/{user_id}/balance", response_model=BalanceResponse)
async def admin_get_user_balance(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get a user's token balance and stats."""
    token_service = TokenService(db)
    stats = await token_service.get_user_stats(user_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return BalanceResponse(**stats)


@router.get("/admin/user/{user_id}/transactions", response_model=List[TransactionResponse])
async def admin_get_user_transactions(
    user_id: int,
    transaction_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get a user's transaction history."""
    token_service = TokenService(db)
    transactions = await token_service.get_transactions(
        user_id=user_id,
        transaction_type=transaction_type,
        skip=skip,
        limit=limit,
    )
    return transactions


@router.post("/admin/user/{user_id}/recharge", response_model=OperationResponse)
async def admin_recharge_user(
    user_id: int,
    request_data: RechargeRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Recharge tokens to a user's balance."""
    token_service = TokenService(db)

    success, new_balance, transaction = await token_service.recharge(
        user_id=user_id,
        amount=request_data.amount,
        order_no=request_data.order_no,
        description=request_data.description or f"Admin recharge by {current_user.username}",
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to recharge tokens. User may not exist.",
        )

    tx_response = None
    if transaction:
        tx_response = TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            transaction_type=transaction.transaction_type,
            description=transaction.description,
            order_no=transaction.order_no,
            api_key_id=transaction.api_key_id,
            created_at=transaction.created_at,
        )

    return OperationResponse(
        success=True,
        new_balance=new_balance,
        transaction=tx_response,
        message="Tokens recharged successfully",
    )


@router.post("/admin/user/{user_id}/consume", response_model=OperationResponse)
async def admin_consume_user(
    user_id: int,
    request_data: ConsumeRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Consume tokens from a user's balance."""
    token_service = TokenService(db)

    success, new_balance, transaction = await token_service.consume(
        user_id=user_id,
        amount=request_data.amount,
        api_key_id=request_data.api_key_id,
        description=request_data.description or f"Admin consumption by {current_user.username}",
        apply_discount=request_data.apply_discount,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to consume tokens. Insufficient balance or user not found.",
        )

    tx_response = None
    if transaction:
        tx_response = TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            transaction_type=transaction.transaction_type,
            description=transaction.description,
            order_no=transaction.order_no,
            api_key_id=transaction.api_key_id,
            created_at=transaction.created_at,
        )

    return OperationResponse(
        success=True,
        new_balance=new_balance,
        transaction=tx_response,
        message="Tokens consumed successfully",
    )


@router.post("/admin/user/{user_id}/refund", response_model=OperationResponse)
async def admin_refund_user(
    user_id: int,
    request_data: RefundRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Refund tokens to a user's balance."""
    token_service = TokenService(db)

    success, new_balance, transaction = await token_service.refund(
        user_id=user_id,
        amount=request_data.amount,
        order_no=request_data.order_no,
        description=request_data.description or f"Admin refund by {current_user.username}",
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to refund tokens. User may not exist.",
        )

    tx_response = None
    if transaction:
        tx_response = TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            transaction_type=transaction.transaction_type,
            description=transaction.description,
            order_no=transaction.order_no,
            api_key_id=transaction.api_key_id,
            created_at=transaction.created_at,
        )

    return OperationResponse(
        success=True,
        new_balance=new_balance,
        transaction=tx_response,
        message="Tokens refunded successfully",
    )


@router.post("/admin/user/{user_id}/adjust", response_model=OperationResponse)
async def admin_adjust_user(
    user_id: int,
    request_data: AdjustRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Adjust a user's balance (add or deduct)."""
    token_service = TokenService(db)

    success, new_balance, transaction = await token_service.adjust(
        user_id=user_id,
        amount=request_data.amount,
        description=request_data.description or f"Admin adjustment by {current_user.username}",
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to adjust balance. Would result in negative balance or user not found.",
        )

    tx_response = None
    if transaction:
        tx_response = TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            transaction_type=transaction.transaction_type,
            description=transaction.description,
            order_no=transaction.order_no,
            api_key_id=transaction.api_key_id,
            created_at=transaction.created_at,
        )

    return OperationResponse(
        success=True,
        new_balance=new_balance,
        transaction=tx_response,
        message="Balance adjusted successfully",
    )


@router.post("/admin/user/{user_id}/discount", response_model=dict)
async def admin_set_user_discount(
    user_id: int,
    request_data: SetDiscountRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Set a user's discount rate."""
    token_service = TokenService(db)

    success = await token_service.set_discount(
        user_id=user_id,
        discount_rate=request_data.discount_rate,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to set discount. Invalid rate or user not found.",
        )

    discount_percent = int((1 - request_data.discount_rate) * 100)
    return {
        "success": True,
        "discount_rate": request_data.discount_rate,
        "discount_percent": discount_percent,
        "message": f"Discount set to {discount_percent}% off" if discount_percent > 0 else "No discount (full price)",
    }
