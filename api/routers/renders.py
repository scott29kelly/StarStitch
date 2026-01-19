"""
Renders Router
REST endpoints for managing render jobs.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from ..models.render import (
    RenderListResponse,
    RenderRequest,
    RenderResponse,
    RenderStatus,
)
from ..services.job_manager import job_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["renders"])


@router.post("/render", response_model=RenderResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_render(
    request: RenderRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new render job.

    Creates a render job and starts processing in the background.
    Use WebSocket at /ws/progress/{id} to receive real-time updates.
    """
    # Check if we can start a new job
    if not job_manager.can_start_job():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum concurrent jobs reached. Please wait for a job to complete.",
        )

    # Validate sequence has at least 2 subjects
    if len(request.sequence) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 subjects are required for morphing.",
        )

    # Create the job
    job = await job_manager.create_job(request)

    # Import here to avoid circular imports
    from ..services.render_service import execute_render_job

    # Add render task to background
    background_tasks.add_task(execute_render_job, job.id)

    logger.info(f"Started render job {job.id} for project '{request.project_name}'")

    return job.to_response()


@router.get("/render/{job_id}", response_model=RenderResponse)
async def get_render_status(job_id: str):
    """
    Get the status of a render job.

    Returns current progress, status, and output path (if complete).
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return job.to_response()


@router.delete("/render/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_render(job_id: str):
    """
    Cancel a running render job.

    Only pending or running jobs can be cancelled.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job.status not in (RenderStatus.PENDING, RenderStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status}'",
        )

    success = await job_manager.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job",
        )


@router.get("/renders", response_model=RenderListResponse)
async def list_renders(
    status: Optional[RenderStatus] = None,
    limit: int = 50,
):
    """
    List all render jobs.

    Optionally filter by status. Returns jobs sorted by creation date (newest first).
    """
    jobs = await job_manager.list_jobs(status=status)
    jobs = jobs[:limit]

    return RenderListResponse(
        renders=[job.to_response() for job in jobs],
        total=len(jobs),
    )
