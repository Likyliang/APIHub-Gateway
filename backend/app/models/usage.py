"""
Usage Record and Statistics Models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class UsageRecord(Base):
    """Individual API call usage record."""

    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)

    # References
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)

    # Request details
    request_id = Column(String(64), unique=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    model = Column(String(100), nullable=True)

    # Usage metrics
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Cost calculation (if applicable)
    cost = Column(Float, default=0.0)

    # Response details
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    is_streaming = Column(Boolean, default=False)
    is_success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="usage_records")
    api_key = relationship("APIKey", back_populates="usage_records")

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_usage_user_date', 'user_id', 'created_at'),
        Index('idx_usage_key_date', 'api_key_id', 'created_at'),
        Index('idx_usage_model_date', 'model', 'created_at'),
    )

    def __repr__(self):
        return f"<UsageRecord(id={self.id}, model='{self.model}', tokens={self.total_tokens})>"


class UsageStats(Base):
    """Aggregated usage statistics (hourly/daily)."""

    __tablename__ = "usage_stats"

    id = Column(Integer, primary_key=True, index=True)

    # Aggregation scope
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    model = Column(String(100), nullable=True)

    # Time period
    period_type = Column(String(10), nullable=False)  # 'hour', 'day', 'month'
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Aggregated metrics
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    avg_response_time_ms = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_stats_user_period', 'user_id', 'period_type', 'period_start'),
        Index('idx_stats_key_period', 'api_key_id', 'period_type', 'period_start'),
    )

    def __repr__(self):
        return f"<UsageStats(id={self.id}, period='{self.period_type}', requests={self.request_count})>"
