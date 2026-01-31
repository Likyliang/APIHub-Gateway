"""
API Key Model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class APIKey(Base):
    """API Key model for authentication and access control."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, index=True, nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed version for security
    name = Column(String(100), nullable=False)  # User-friendly name
    description = Column(Text, nullable=True)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Rate limiting (per key)
    rate_limit = Column(Integer, default=60)  # Requests per minute
    rate_limit_day = Column(Integer, nullable=True)  # Requests per day (None = unlimited)

    # Quota (per key, overrides user quota if set)
    quota_limit = Column(Float, nullable=True)  # None means use user quota
    quota_used = Column(Float, default=0.0)

    # Token system
    token_limit = Column(Float, nullable=True)  # Total token limit (None = unlimited)
    token_used = Column(Float, default=0.0)  # Tokens consumed

    # Pricing & Discount
    discount_rate = Column(Float, default=1.0)  # < 1.0 means discount, e.g., 0.8 = 20% off

    # Allowed models (JSON list, empty means all)
    allowed_models = Column(Text, default="[]")  # JSON array of model names

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    total_requests = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)  # Actual cost after discount

    # Batch creation tracking
    batch_id = Column(String(64), nullable=True, index=True)  # For batch created keys

    # Relationships
    owner = relationship("User", back_populates="api_keys")
    usage_records = relationship("UsageRecord", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', key='{self.key[:12]}...')>"
