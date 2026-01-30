"""
Payment Model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class PaymentMethod(str, enum.Enum):
    WECHAT = "wechat"
    ALIPAY = "alipay"


class Payment(Base):
    """Payment record model."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Order info
    order_no = Column(String(64), unique=True, index=True, nullable=False)
    trade_no = Column(String(128), nullable=True)  # Third-party order number

    # Payment details
    amount = Column(Float, nullable=False)  # Payment amount in CNY
    quota_amount = Column(Float, nullable=False)  # Quota to add
    method = Column(String(20), nullable=False)  # wechat, alipay
    status = Column(String(20), default=PaymentStatus.PENDING.value)

    # Payment gateway info
    gateway = Column(String(50), nullable=True)  # e.g., "epay", "payjs", etc.
    gateway_order_id = Column(String(128), nullable=True)
    qr_code = Column(Text, nullable=True)  # QR code URL or data
    pay_url = Column(Text, nullable=True)  # Payment URL

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    user = relationship("User", backref="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, order_no='{self.order_no}', amount={self.amount})>"


class PricePlan(Base):
    """Pricing plan model."""

    __tablename__ = "price_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price = Column(Float, nullable=False)  # Price in CNY
    quota_amount = Column(Float, nullable=False)  # Quota units

    # Display
    is_popular = Column(Integer, default=0)  # 1 if this is the popular/recommended plan
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PricePlan(id={self.id}, name='{self.name}', price={self.price})>"
