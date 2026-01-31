"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "APIHub-Gateway"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./apihub.db"

    # Security
    secret_key: str = Field(default="your-super-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Upstream proxy (CLIProxyAPI)
    upstream_url: str = "http://127.0.0.1:8317"
    upstream_timeout: int = 300  # 5 minutes for long requests
    upstream_api_key: str = ""  # 上游服务的 API Key (如果需要)

    # API Key settings
    api_key_prefix: str = "ahg"  # APIHub-Gateway prefix

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin123"  # Change in production
    admin_email: str = "admin@apihub.local"

    # Payment (EPay / 易支付)
    epay_url: str = "https://pay.example.com"  # 易支付网关地址
    epay_pid: str = "1000"  # 商户ID
    epay_key: str = "your_epay_key"  # 商户密钥
    payment_notify_url: str = ""  # 支付回调通知地址 (留空则自动生成)
    payment_return_url: str = ""  # 支付完成跳转地址 (留空则自动生成)

    # Site settings
    site_name: str = "APIHub Gateway"
    site_url: str = "http://localhost:3000"
    allow_registration: bool = True  # 是否允许新用户注册

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


settings = get_settings()
