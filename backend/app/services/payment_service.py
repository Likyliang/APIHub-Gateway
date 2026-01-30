"""
Payment Service - Business logic for payment processing
"""
import hashlib
import time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.payment import Payment, PricePlan, PaymentStatus
from ..models.user import User
from ..config import settings


class PaymentService:
    """Service for payment processing operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_order_no(self) -> str:
        """Generate unique order number."""
        timestamp = int(time.time() * 1000)
        random_part = secrets.token_hex(4)
        return f"AHG{timestamp}{random_part}"

    async def create_order(
        self,
        user_id: int,
        plan_id: int,
        method: str,
    ) -> tuple[Payment, dict]:
        """Create a payment order."""
        # Get price plan
        plan = await self.get_plan_by_id(plan_id)
        if not plan or not plan.is_active:
            raise ValueError("Invalid price plan")

        # Create payment record
        order_no = self._generate_order_no()
        payment = Payment(
            user_id=user_id,
            order_no=order_no,
            amount=plan.price,
            quota_amount=plan.quota_amount,
            method=method,
            status=PaymentStatus.PENDING.value,
            expired_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )

        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)

        # Generate payment URL (using EPay as example)
        pay_data = await self._create_epay_order(payment, plan)

        # Update payment with gateway info
        payment.pay_url = pay_data.get("pay_url")
        payment.qr_code = pay_data.get("qr_code")
        payment.gateway = "epay"

        return payment, pay_data

    async def _create_epay_order(self, payment: Payment, plan: PricePlan) -> dict:
        """Create order via EPay gateway (易支付)."""
        # EPay configuration from settings
        epay_url = getattr(settings, "epay_url", "https://pay.example.com")
        epay_pid = getattr(settings, "epay_pid", "1000")
        epay_key = getattr(settings, "epay_key", "your_epay_key")
        notify_url = getattr(settings, "payment_notify_url", f"{settings.upstream_url}/api/payment/notify")
        return_url = getattr(settings, "payment_return_url", f"{settings.upstream_url}/payment/success")

        # Build sign
        params = {
            "pid": epay_pid,
            "type": payment.method,  # wechat or alipay
            "out_trade_no": payment.order_no,
            "notify_url": notify_url,
            "return_url": return_url,
            "name": f"APIHub配额充值 - {plan.name}",
            "money": f"{payment.amount:.2f}",
        }

        # Generate sign (MD5)
        sign_str = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
        sign_str += epay_key
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        params["sign"] = sign
        params["sign_type"] = "MD5"

        # Build payment URL
        pay_url = f"{epay_url}/submit.php?" + "&".join(f"{k}={v}" for k, v in params.items())

        return {
            "pay_url": pay_url,
            "qr_code": None,  # EPay will redirect to QR code page
            "order_no": payment.order_no,
        }

    async def handle_notify(self, data: dict) -> bool:
        """Handle payment notification callback."""
        # Verify sign
        epay_key = getattr(settings, "epay_key", "your_epay_key")
        received_sign = data.pop("sign", "")
        sign_type = data.pop("sign_type", "MD5")

        # Calculate expected sign
        sign_str = "&".join(f"{k}={data[k]}" for k in sorted(data.keys()) if data[k])
        sign_str += epay_key
        expected_sign = hashlib.md5(sign_str.encode()).hexdigest()

        if received_sign != expected_sign:
            return False

        # Get payment
        order_no = data.get("out_trade_no")
        trade_no = data.get("trade_no")
        trade_status = data.get("trade_status")

        payment = await self.get_payment_by_order_no(order_no)
        if not payment:
            return False

        if payment.status == PaymentStatus.PAID.value:
            return True  # Already processed

        if trade_status == "TRADE_SUCCESS":
            # Update payment status
            payment.status = PaymentStatus.PAID.value
            payment.trade_no = trade_no
            payment.paid_at = datetime.now(timezone.utc)

            # Add quota to user
            user = await self.db.get(User, payment.user_id)
            if user:
                user.quota_limit += payment.quota_amount

            return True

        return False

    async def get_payment_by_order_no(self, order_no: str) -> Optional[Payment]:
        """Get payment by order number."""
        result = await self.db.execute(
            select(Payment).where(Payment.order_no == order_no)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        return await self.db.get(Payment, payment_id)

    async def get_user_payments(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Payment]:
        """Get user's payment history."""
        result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def check_payment_status(self, order_no: str) -> Optional[Payment]:
        """Check and update payment status."""
        payment = await self.get_payment_by_order_no(order_no)
        if not payment:
            return None

        # Check if expired
        if (
            payment.status == PaymentStatus.PENDING.value
            and payment.expired_at
            and payment.expired_at < datetime.now(timezone.utc)
        ):
            payment.status = PaymentStatus.EXPIRED.value

        return payment

    # Price Plan methods
    async def get_plan_by_id(self, plan_id: int) -> Optional[PricePlan]:
        """Get price plan by ID."""
        return await self.db.get(PricePlan, plan_id)

    async def get_active_plans(self) -> List[PricePlan]:
        """Get all active price plans."""
        result = await self.db.execute(
            select(PricePlan)
            .where(PricePlan.is_active == 1)
            .order_by(PricePlan.sort_order)
        )
        return list(result.scalars().all())

    async def create_plan(
        self,
        name: str,
        price: float,
        quota_amount: float,
        description: str = None,
        is_popular: bool = False,
        sort_order: int = 0,
    ) -> PricePlan:
        """Create a new price plan."""
        plan = PricePlan(
            name=name,
            price=price,
            quota_amount=quota_amount,
            description=description,
            is_popular=1 if is_popular else 0,
            sort_order=sort_order,
        )
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def update_plan(self, plan_id: int, **kwargs) -> Optional[PricePlan]:
        """Update a price plan."""
        plan = await self.get_plan_by_id(plan_id)
        if not plan:
            return None

        for key, value in kwargs.items():
            if hasattr(plan, key):
                setattr(plan, key, value)

        return plan

    async def delete_plan(self, plan_id: int) -> bool:
        """Soft delete a price plan."""
        plan = await self.get_plan_by_id(plan_id)
        if not plan:
            return False
        plan.is_active = 0
        return True

    async def get_payment_stats(self) -> Dict[str, Any]:
        """Get payment statistics (admin)."""
        from sqlalchemy import func

        # Total revenue
        total_result = await self.db.execute(
            select(
                func.count(Payment.id).label("total_orders"),
                func.sum(Payment.amount).label("total_amount"),
            ).where(Payment.status == PaymentStatus.PAID.value)
        )
        total_row = total_result.one()

        # Today's revenue
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await self.db.execute(
            select(
                func.count(Payment.id).label("today_orders"),
                func.sum(Payment.amount).label("today_amount"),
            ).where(
                and_(
                    Payment.status == PaymentStatus.PAID.value,
                    Payment.paid_at >= today_start,
                )
            )
        )
        today_row = today_result.one()

        return {
            "total_orders": total_row.total_orders or 0,
            "total_revenue": float(total_row.total_amount or 0),
            "today_orders": today_row.today_orders or 0,
            "today_revenue": float(today_row.today_amount or 0),
        }
