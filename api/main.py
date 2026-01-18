"""
StarStitch API Server
FastAPI application for the StarStitch video morphing pipeline.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .routes import render_router, templates_router
from .websocket import websocket_endpoint
from .job_queue import job_queue

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Starts the job queue worker on startup and stops it on shutdown.
    """
    # Startup
    logger.info("Starting StarStitch API Server...")
    
    # Start job queue
    await job_queue.start()
    
    # Configure pipeline factory
    def pipeline_factory(config, on_progress=None, variants_override=None):
        from main import StarStitchPipeline
        return StarStitchPipeline(
            config=config,
            on_progress=on_progress,
            variants_override=variants_override,
        )
    
    job_queue.set_pipeline_factory(pipeline_factory)
    
    logger.info("StarStitch API Server ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down StarStitch API Server...")
    await job_queue.stop()
    logger.info("StarStitch API Server stopped")


# Create FastAPI application
app = FastAPI(
    title="StarStitch API",
    description="""
    ## StarStitch - AI-Powered Video Morphing Pipeline
    
    RESTful API for programmatic access to the StarStitch video morphing pipeline.
    
    ### Features
    
    - **Render Jobs**: Submit, monitor, and cancel render jobs
    - **Real-time Updates**: WebSocket connections for live progress updates
    - **Templates**: Browse and use pre-built scene templates
    - **Batch Processing**: Queue multiple renders for sequential processing
    
    ### Getting Started
    
    1. **Start a render**: `POST /api/render` with your configuration
    2. **Monitor progress**: Connect to WebSocket at `/ws/render/{job_id}`
    3. **Check status**: `GET /api/render/{job_id}` for current state
    
    ### WebSocket Protocol
    
    Connect to `/ws/render/{job_id}` to receive real-time updates:
    
    - `state`: Initial state when connecting
    - `progress`: Step-by-step progress updates
    - `complete`: Render finished successfully
    - `error`: Render failed with error
    - `cancelled`: Render was cancelled
    
    Send `{"type": "ping"}` for heartbeat, `{"type": "cancel"}` to cancel.
    """,
    version="0.6.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(render_router)
app.include_router(templates_router)


# WebSocket endpoint
@app.websocket("/ws/render/{job_id}")
async def websocket_render(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time render progress updates.
    
    Connect to receive updates for a specific render job.
    """
    await websocket_endpoint(websocket, job_id)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the server status and configuration.
    """
    return {
        "status": "healthy",
        "version": "0.6.0",
        "queue": {
            "max_concurrent": job_queue.max_concurrent,
            "pending_jobs": job_queue._pending_queue.qsize(),
            "running_jobs": len(job_queue._running_jobs),
            "total_jobs": len(job_queue._jobs),
        },
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "StarStitch API",
        "version": "0.6.0",
        "description": "AI-Powered Video Morphing Pipeline",
        "docs": "/docs",
        "health": "/health",
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if os.getenv("DEBUG") else None,
        }
    )


# Static files for renders (optional - mount if renders folder exists)
renders_path = Path("renders")
if renders_path.exists():
    app.mount("/renders", StaticFiles(directory="renders"), name="renders")


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Run the API server.
    
    Args:
        host: Host to bind to.
        port: Port to bind to.
        reload: Enable auto-reload for development.
    """
    import uvicorn
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="StarStitch API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, reload=args.reload)
