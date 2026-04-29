"""
api/main.py
-----------
FastAPI application entry point.
Mounts all routers, middleware, WebSocket endpoint, and lifecycle hooks.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from api.config import get_settings
from api.routes import router
from api.websocket import ws_router
from api.middleware import LoggingMiddleware, RateLimitMiddleware
from utils.logger import get_logger

logger = get_logger("api.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENV}")
    logger.info("=" * 60)

    # Initialize DB tables and seed data
    try:
        from database.models import create_all_tables
        create_all_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

    # Preload the AI model
    try:
        from ai_model.model_loader import ModelLoader
        ModelLoader.get_instance()
        logger.info("AI model loaded successfully")
    except Exception as e:
        logger.warning(f"AI model load failed (predictions disabled): {e}")

    # Create default admin user if not exists
    try:
        _ensure_default_admin()
    except Exception as e:
        logger.warning(f"Default admin creation skipped: {e}")

    yield

    logger.info("Shutting down Spectrum API...")


def _ensure_default_admin():
    """Create default admin account on first run."""
    import sqlite3
    from security.auth import hash_password
    from datetime import datetime

    conn = sqlite3.connect("spectrum.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            ("admin", hash_password("admin123"), "Admin", datetime.now().isoformat()),
        )
        conn.commit()
        logger.info("Default admin user created (username: admin, password: admin123)")
    conn.close()


# ── FastAPI app instance ─────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered RF Spectrum Anomaly Detection System",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)

# ── Routers ──────────────────────────────────────────────────────────

app.include_router(router, prefix="/api/v1")
app.include_router(ws_router)


# ── Root endpoint ────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "env": settings.ENV}


# ── Global exception handler ─────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
