"""
Render Routes
REST API endpoints for render job management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..models import (
    ErrorResponse,
    JobState,
    RenderListItem,
    RenderListResponse,
    RenderRequest,
    RenderResponse,
    RenderStatus,
)
from ..job_queue import job_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Render"])


@router.post(
    "/render",
    response_model=RenderResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Start a new render",
    description="Submit a new render job to the queue. Returns a job ID for tracking progress.",
)
async def start_render(request: Request, render_request: RenderRequest):
    """
    Start a new render job.
    
    The job will be queued for processing. Use the returned job_id to:
    - Poll status via GET /api/render/{job_id}
    - Subscribe to real-time updates via WebSocket /ws/render/{job_id}
    """
    try:
        # Convert request to config dict
        config = render_request.model_dump(exclude_none=True)
        
        # Handle template if specified
        if render_request.template_name:
            from utils import TemplateLoader
            loader = TemplateLoader()
            try:
                config = loader.apply_template(render_request.template_name, config)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Validate sequence
        if len(config.get("sequence", [])) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 subjects are required for morphing"
            )
        
        # Create and enqueue job
        job = job_queue.create_job(config)
        await job_queue.enqueue(job.job_id)
        
        # Build WebSocket URL
        host = request.headers.get("host", "localhost:8000")
        scheme = "wss" if request.url.scheme == "https" else "ws"
        ws_url = f"{scheme}://{host}/ws/render/{job.job_id}"
        
        logger.info(f"Render job {job.job_id} created for project '{job.project_name}'")
        
        return RenderResponse(
            job_id=job.job_id,
            message=f"Render job queued for project '{job.project_name}'",
            state=job.state,
            websocket_url=ws_url,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create render job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/render/{job_id}",
    response_model=RenderStatus,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
    summary="Get render status",
    description="Get the current status and progress of a render job.",
)
async def get_render_status(job_id: str):
    """
    Get the status of a render job.
    
    Returns the current state, progress details, and output path if complete.
    """
    status = job_queue.get_job_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    return status


@router.delete(
    "/render/{job_id}",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
        409: {"model": ErrorResponse, "description": "Cannot cancel job"},
    },
    summary="Cancel a render",
    description="Cancel a pending or running render job.",
)
async def cancel_render(job_id: str):
    """
    Cancel a render job.
    
    - Pending jobs are immediately cancelled
    - Running jobs will be stopped at the next checkpoint
    - Completed jobs cannot be cancelled
    """
    job = job_queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    if job.state == JobState.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel a completed job"
        )
    
    success = job_queue.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Failed to cancel job '{job_id}'"
        )
    
    logger.info(f"Job {job_id} cancellation requested")
    
    return {
        "job_id": job_id,
        "message": "Cancellation requested",
        "state": job.state.value,
    }


@router.get(
    "/renders",
    response_model=RenderListResponse,
    summary="List all renders",
    description="List all render jobs with pagination and optional state filtering.",
)
async def list_renders(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
):
    """
    List all render jobs.
    
    Supports pagination and filtering by job state.
    """
    # Parse state filter
    state_filter = None
    if state:
        try:
            state_filter = JobState(state)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state filter. Valid values: {[s.value for s in JobState]}"
            )
    
    jobs, total = job_queue.list_jobs(page=page, page_size=page_size, state_filter=state_filter)
    
    # Convert to list items
    items = [
        RenderListItem(
            job_id=job.job_id,
            project_name=job.project_name,
            state=job.state,
            created_at=job.created_at,
            completed_at=job.completed_at,
            output_path=job.output_path,
            subjects_count=job.subjects_count,
            progress_percent=job.progress.progress_percent if job.progress else 0,
        )
        for job in jobs
    ]
    
    has_more = (page * page_size) < total
    
    return RenderListResponse(
        renders=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.delete(
    "/renders/{job_id}",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
        409: {"model": ErrorResponse, "description": "Cannot delete running job"},
    },
    summary="Delete a render from history",
    description="Remove a completed, failed, or cancelled render from history.",
)
async def delete_render(job_id: str):
    """
    Delete a render job from history.
    
    Running jobs cannot be deleted - cancel them first.
    """
    job = job_queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    if job.state == JobState.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a running job. Cancel it first."
        )
    
    success = job_queue.delete_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job '{job_id}'"
        )
    
    return {
        "job_id": job_id,
        "message": "Job deleted from history",
    }
