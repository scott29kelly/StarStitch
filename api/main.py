"""
StarStitch API
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import renders_router, templates_router, websocket_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(f"Starting StarStitch API v{settings.api_version}")
    logger.info(f"Renders directory: {settings.renders_dir}")
    logger.info(f"Templates directory: {settings.templates_dir}")

    # Ensure directories exist
    settings.renders_dir.mkdir(parents=True, exist_ok=True)
    settings.templates_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    logger.info("Shutting down StarStitch API")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
StarStitch API - AI-Powered Video Morphing Pipeline

## Features

- **Render Management**: Create, monitor, and cancel render jobs
- **Real-time Progress**: WebSocket streaming for live progress updates
- **Template Library**: Browse and apply pre-built scene templates

## Quick Start

1. **Start a render**: POST to `/api/render` with your project configuration
2. **Monitor progress**: Connect to `/ws/progress/{job_id}` for real-time updates
3. **Check status**: GET `/api/render/{job_id}` for current status

## WebSocket Protocol

Connect to `/ws/progress/{job_id}` to receive JSON progress events:

```json
{
    "type": "progress",
    "job_id": "render_abc123",
    "progress_percent": 30.0,
    "message": "Generating image for Artist..."
}
```
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(renders_router)
app.include_router(templates_router)
app.include_router(websocket_router)


@app.get("/", tags=["health"])
async def root():
    """API root endpoint."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.api_version,
    }
