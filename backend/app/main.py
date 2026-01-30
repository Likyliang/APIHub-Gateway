"""
APIHub-Gateway - Main Application
API Key Management and Distribution Platform for CLIProxyAPI
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from .config import settings
from .database import init_db, close_db, async_session_maker
from .routers import auth_router, keys_router, usage_router, users_router, proxy_router, payment_router
from .services.user_service import UserService
from .services.payment_service import PaymentService


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.debug else "INFO",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting APIHub-Gateway...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create default admin user if not exists
    async with async_session_maker() as db:
        user_service = UserService(db)
        admin = await user_service.get_user_by_username(settings.admin_username)
        if not admin:
            admin = await user_service.create_user(
                username=settings.admin_username,
                email=settings.admin_email,
                password=settings.admin_password,
                is_admin=True,
                quota_limit=float("inf"),
            )
            await db.commit()
            logger.info(f"Created default admin user: {settings.admin_username}")

        # Create default price plans if not exist
        payment_service = PaymentService(db)
        plans = await payment_service.get_active_plans()
        if not plans:
            await payment_service.create_plan(
                name="入门套餐",
                price=9.9,
                quota_amount=100,
                description="适合个人轻度使用",
                sort_order=1,
            )
            await payment_service.create_plan(
                name="标准套餐",
                price=29.9,
                quota_amount=500,
                description="适合日常开发使用",
                is_popular=True,
                sort_order=2,
            )
            await payment_service.create_plan(
                name="专业套餐",
                price=99.9,
                quota_amount=2000,
                description="适合团队和重度使用",
                sort_order=3,
            )
            await payment_service.create_plan(
                name="企业套餐",
                price=299.9,
                quota_amount=10000,
                description="无限制企业级使用",
                sort_order=4,
            )
            await db.commit()
            logger.info("Created default price plans")

    logger.info(f"APIHub-Gateway started on {settings.host}:{settings.port}")
    logger.info(f"Upstream proxy: {settings.upstream_url}")

    yield

    # Cleanup
    await close_db()
    logger.info("APIHub-Gateway stopped")


# Create FastAPI app
app = FastAPI(
    title="APIHub-Gateway",
    description="API Key Management and Distribution Platform for CLIProxyAPI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(keys_router, prefix="/api")
app.include_router(usage_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(payment_router, prefix="/api")
app.include_router(proxy_router)  # Proxy routes at root level


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "APIHub-Gateway",
        "version": "1.0.0",
        "description": "API Key Management and Distribution Platform",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
