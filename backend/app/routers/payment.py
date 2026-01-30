"""
Payment Routes
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.payment_service import PaymentService
from ..middleware.auth import get_current_active_user, get_admin_user
from ..models.user import User


router = APIRouter(prefix="/payment", tags=["Payment"])


class PricePlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    quota_amount: float
    is_popular: bool

    class Config:
        from_attributes = True


class CreateOrderRequest(BaseModel):
    plan_id: int
    method: str  # wechat, alipay


class OrderResponse(BaseModel):
    order_no: str
    amount: float
    quota_amount: float
    method: str
    status: str
    pay_url: Optional[str]
    qr_code: Optional[str]
    created_at: datetime
    expired_at: Optional[datetime]


class PaymentRecordResponse(BaseModel):
    id: int
    order_no: str
    amount: float
    quota_amount: float
    method: str
    status: str
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class PricePlanCreate(BaseModel):
    name: str
    price: float
    quota_amount: float
    description: Optional[str] = None
    is_popular: bool = False
    sort_order: int = 0


# Public endpoints
@router.get("/plans", response_model=List[PricePlanResponse])
async def get_price_plans(
    db: AsyncSession = Depends(get_db),
):
    """Get all available price plans."""
    payment_service = PaymentService(db)
    plans = await payment_service.get_active_plans()
    return [
        PricePlanResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            quota_amount=p.quota_amount,
            is_popular=bool(p.is_popular),
        )
        for p in plans
    ]


# User endpoints (require auth)
@router.post("/order", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new payment order."""
    if request.method not in ["wechat", "alipay"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method",
        )

    payment_service = PaymentService(db)

    try:
        payment, pay_data = await payment_service.create_order(
            user_id=current_user.id,
            plan_id=request.plan_id,
            method=request.method,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return OrderResponse(
        order_no=payment.order_no,
        amount=payment.amount,
        quota_amount=payment.quota_amount,
        method=payment.method,
        status=payment.status,
        pay_url=pay_data.get("pay_url"),
        qr_code=pay_data.get("qr_code"),
        created_at=payment.created_at,
        expired_at=payment.expired_at,
    )


@router.get("/order/{order_no}", response_model=OrderResponse)
async def get_order_status(
    order_no: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check order status."""
    payment_service = PaymentService(db)
    payment = await payment_service.check_payment_status(order_no)

    if not payment or payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderResponse(
        order_no=payment.order_no,
        amount=payment.amount,
        quota_amount=payment.quota_amount,
        method=payment.method,
        status=payment.status,
        pay_url=payment.pay_url,
        qr_code=payment.qr_code,
        created_at=payment.created_at,
        expired_at=payment.expired_at,
    )


@router.get("/history", response_model=List[PaymentRecordResponse])
async def get_payment_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's payment history."""
    payment_service = PaymentService(db)
    payments = await payment_service.get_user_payments(
        current_user.id, skip=skip, limit=limit
    )
    return payments


# Payment callback endpoint (no auth required, verified by sign)
@router.get("/notify")
@router.post("/notify")
async def payment_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle payment gateway callback."""
    # Get data from query params or form
    if request.method == "GET":
        data = dict(request.query_params)
    else:
        form = await request.form()
        data = dict(form)

    payment_service = PaymentService(db)
    success = await payment_service.handle_notify(data)

    if success:
        return PlainTextResponse("success")
    else:
        return PlainTextResponse("fail")


# Admin endpoints
@router.get("/admin/stats")
async def get_payment_stats(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment statistics (admin only)."""
    payment_service = PaymentService(db)
    return await payment_service.get_payment_stats()


@router.post("/admin/plans", response_model=PricePlanResponse)
async def create_plan(
    plan_data: PricePlanCreate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new price plan (admin only)."""
    payment_service = PaymentService(db)
    plan = await payment_service.create_plan(
        name=plan_data.name,
        price=plan_data.price,
        quota_amount=plan_data.quota_amount,
        description=plan_data.description,
        is_popular=plan_data.is_popular,
        sort_order=plan_data.sort_order,
    )
    return PricePlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        price=plan.price,
        quota_amount=plan.quota_amount,
        is_popular=bool(plan.is_popular),
    )


@router.put("/admin/plans/{plan_id}", response_model=PricePlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: PricePlanCreate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a price plan (admin only)."""
    payment_service = PaymentService(db)
    plan = await payment_service.update_plan(
        plan_id,
        name=plan_data.name,
        price=plan_data.price,
        quota_amount=plan_data.quota_amount,
        description=plan_data.description,
        is_popular=1 if plan_data.is_popular else 0,
        sort_order=plan_data.sort_order,
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    return PricePlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        price=plan.price,
        quota_amount=plan.quota_amount,
        is_popular=bool(plan.is_popular),
    )


@router.delete("/admin/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a price plan (admin only)."""
    payment_service = PaymentService(db)
    success = await payment_service.delete_plan(plan_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    return {"message": "Plan deleted"}
