"""MIRROR AI — FastAPI Application Entry Point.

This is the main application factory. It:
- Configures logging
- Sets up CORS
- Registers all API routers
- Provides the lifespan hooks for startup/shutdown
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_analysis import router as analysis_router
from app.api.routes_health import router as health_router
from app.api.routes_profile import router as profile_router
from app.api.routes_repos import router as repos_router
from app.api.routes_roles import router as roles_router
from app.config import settings
from app.logging_config import get_logger, setup_logging

# Configure logging before anything else
setup_logging(debug=settings.app_debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info(
        "app_starting",
        environment=settings.app_env,
        debug=settings.app_debug,
    )
    yield
    logger.info("app_shutting_down")


# ── Create the FastAPI application ───────────────────────────────

app = FastAPI(
    title="MIRROR AI",
    description=(
        "Developer Intelligence Platform — models observable engineering "
        "behavior from GitHub history and produces evidence-backed profiles."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── CORS ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ────────────────────────────────────────────

app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(profile_router)
app.include_router(repos_router)
app.include_router(roles_router)


# ── Root redirect ────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs or return a welcome message."""
    return {
        "name": "MIRROR AI",
        "version": "0.1.0",
        "tagline": "See how you build.",
        "docs": "/docs",
        "health": "/health",
    }
