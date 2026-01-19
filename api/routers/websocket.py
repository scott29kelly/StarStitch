"""
WebSocket Router
WebSocket endpoint for real-time progress streaming.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.job_manager import job_manager
from ..services.websocket_manager import ws_manager
from ..models.progress import ProgressEvent, ProgressEventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time render progress.

    Connect to receive progress events for a specific render job.

    Events are JSON objects with the following structure:
    {
        "type": "progress",
        "job_id": "render_abc123",
        "timestamp": "2026-01-18T12:00:00Z",
        "current_step": 3,
        "total_steps": 10,
        "progress_percent": 30.0,
        "phase": "image_generation",
        "subject": "Artist",
        "message": "Generating image for Artist..."
    }

    Event types:
    - connected: Initial connection confirmation
    - job_started: Render job has started
    - progress: Generic progress update
    - phase_started: New phase has begun
    - step_progress: Individual step progress
    - job_completed: Render finished successfully
    - job_failed: Render failed with error
    - job_cancelled: Render was cancelled
    - log: Log message from pipeline
    """
    # Check if job exists
    job = await job_manager.get_job(job_id)

    if not job:
        await websocket.close(code=4004, reason=f"Job {job_id} not found")
        return

    # Connect to WebSocket
    await ws_manager.connect(websocket, job_id)

    try:
        # Send initial job status
        event = ProgressEvent(
            type=ProgressEventType.PROGRESS,
            job_id=job_id,
            timestamp=job.updated_at,
            current_step=job.current_step,
            total_steps=job.total_steps,
            progress_percent=job.progress_percent,
            phase=job.current_phase,
            message=job.message,
        )
        await ws_manager.send_personal(websocket, event)

        # Keep connection open and handle messages
        while True:
            try:
                # Wait for any client messages (e.g., ping/pong, cancel request)
                data = await websocket.receive_text()

                # Handle client commands
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "cancel":
                    # Request job cancellation
                    await job_manager.cancel_job(job_id)
                    event = ProgressEvent(
                        type=ProgressEventType.JOB_CANCELLED,
                        job_id=job_id,
                        timestamp=job.updated_at,
                        message="Job cancelled by client request",
                    )
                    await ws_manager.send_personal(websocket, event)

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        await ws_manager.disconnect(websocket, job_id)
