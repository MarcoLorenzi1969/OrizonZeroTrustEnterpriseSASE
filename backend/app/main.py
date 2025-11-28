"""
Orizon Zero Trust Connect - Main Application
For: Marco @ Syneto/Orizon

FastAPI application with:
- JWT Authentication
- RBAC (SuperUser → Super Admin → Admin → User)
- WebSocket support
- PostgreSQL + Redis + MongoDB
- Tunnel management (SSH + HTTPS)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from app.core.config import settings
from app.core.database import init_db, close_db, AsyncSessionLocal
from app.core.redis import redis_client
from app.core.mongodb import mongodb_client
from app.api.v1.router import api_router
from app.tunnel.ssh_server import init_ssh_server


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
)

if not settings.DEBUG:
    logger.add(
        settings.LOG_FILE,
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        level=settings.LOG_LEVEL,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    logger.info("🚀 Starting Orizon Zero Trust Connect...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"📍 Version: {settings.APP_VERSION}")
    
    try:
        # Initialize database
        logger.info("🔌 Connecting to PostgreSQL...")
        await init_db()
        logger.info("✅ PostgreSQL connected")
        
        # Initialize Redis
        logger.info("🔌 Connecting to Redis...")
        await redis_client.connect()
        logger.info("✅ Redis connected")
        
        # Initialize MongoDB
        logger.info("🔌 Connecting to MongoDB...")
        await mongodb_client.connect()
        logger.info("✅ MongoDB connected")

        # Initialize SSH Reverse Tunnel Server
        logger.info("🔌 Starting SSH Reverse Tunnel Server...")
        ssh_mgr = init_ssh_server(AsyncSessionLocal)
        await ssh_mgr.start()
        app.state.ssh_server_manager = ssh_mgr
        logger.info("✅ SSH Reverse Tunnel Server started")

        logger.info("🎉 Application started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("⏹️  Shutting down Orizon Zero Trust Connect...")

    try:
        # Stop SSH server
        if hasattr(app.state, 'ssh_server_manager') and app.state.ssh_server_manager:
            await app.state.ssh_server_manager.stop()

        await close_db()
        await redis_client.disconnect()
        await mongodb_client.disconnect()
        logger.info("✅ All connections closed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
    
    logger.info("👋 Application stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise SD-WAN/Zero Trust Network Platform",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Trusted Host Middleware (production)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "139.59.149.48",
            "46.101.128.1",
            "46.101.189.126",
            "*.orizon.local",
        ]
    )


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Orizon Zero Trust Connect API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs" if settings.DEBUG else "Docs disabled in production",
    }


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
