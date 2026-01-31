"""
User Model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class TokenTransaction(Base):
    """Token transaction history (代币交易记录)."""

    __tablename__ = "token_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Transaction details
    amount = Column(Float, nullable=False)  # Positive = recharge, Negative = consume
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)

    # Transaction type
    transaction_type = Column(String(20), nullable=False)  # recharge, consume, refund, adjust
    description = Column(String(255), nullable=True)

    # Related records
    order_no = Column(String(64), nullable=True, index=True)  # Payment order number
    api_key_id = Column(Integer, nullable=True)  # Related API key for consumption

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="token_transactions")

    def __repr__(self):
        return f"<TokenTransaction(id={self.id}, amount={self.amount}, type='{self.transaction_type}')>"


class User(Base):
    """User model for authentication and ownership."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Quota settings (monthly)
    quota_limit = Column(Float, default=100.0)  # Default 100 units per month
    quota_used = Column(Float, default=0.0)
    quota_reset_date = Column(DateTime(timezone=True), nullable=True)

    # Token/Balance system (代币系统)
    token_balance = Column(Float, default=0.0)  # Current token balance
    total_recharged = Column(Float, default=0.0)  # Total tokens ever recharged
    total_consumed = Column(Float, default=0.0)  # Total tokens ever consumed

    # Discount rate for this user (global discount)
    discount_rate = Column(Float, default=1.0)  # < 1.0 means discount

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    api_keys = relationship("APIKey", back_populates="owner", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    token_transactions = relationship("TokenTransaction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
