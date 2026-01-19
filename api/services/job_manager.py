"""
Job Manager
In-memory job queue and state management for render jobs.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from ..models.render import RenderRequest, RenderResponse, RenderStatus

logger = logging.getLogger(__name__)


class Job(BaseModel):
    """Internal job representation with full state."""
    id: str
    status: RenderStatus
    request: RenderRequest
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress tracking
    current_step: int = 0
    total_steps: int = 0
    current_phase: str = ""
    message: str = ""

    # Results
    output_path: Optional[str] = None
    error: Optional[str] = None

    # Internal
    task: Optional[Any] = None  # asyncio.Task, excluded from serialization

    class Config:
        arbitrary_types_allowed = True

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps == 0:
            return 0.0
        return round((self.current_step / self.total_steps) * 100, 1)

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds."""
        if not self.started_at:
            return 0.0
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    def to_response(self) -> RenderResponse:
        """Convert to API response model."""
        return RenderResponse(
            id=self.id,
            status=self.status,
            project_name=self.request.project_name,
            created_at=self.created_at,
            updated_at=self.updated_at,
            current_step=self.current_step,
            total_steps=self.total_steps,
            progress_percent=self.progress_percent,
            current_phase=self.current_phase,
            message=self.message,
            output_path=self.output_path,
            error=self.error,
            elapsed_seconds=self.elapsed_seconds,
        )

    def update_progress(
        self,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        phase: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Update job progress."""
        if current_step is not None:
            self.current_step = current_step
        if total_steps is not None:
            self.total_steps = total_steps
        if phase is not None:
            self.current_phase = phase
        if message is not None:
            self.message = message
        self.updated_at = datetime.utcnow()


class JobManager:
    """
    In-memory job manager for render jobs.

    Provides:
    - Job creation and tracking
    - Status updates
    - Job cancellation
    - Cleanup of completed jobs
    """

    def __init__(self, max_concurrent: int = 2):
        """Initialize the job manager."""
        self._jobs: Dict[str, Job] = {}
        self._max_concurrent = max_concurrent
        self._lock = asyncio.Lock()

        # Callbacks for job events
        self._on_progress: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable) -> None:
        """Set callback for progress updates."""
        self._on_progress = callback

    async def create_job(self, request: RenderRequest) -> Job:
        """
        Create a new render job.

        Args:
            request: Render request configuration.

        Returns:
            Created job instance.
        """
        job_id = f"render_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        # Calculate total steps: images + morphs + final + audio? + variants?
        num_subjects = len(request.sequence)
        num_morphs = max(0, num_subjects - 1)
        num_variants = len(request.settings.variants)

        total_steps = num_subjects + num_morphs
        if num_variants > 0:
            total_steps += 1
        if request.audio.enabled:
            total_steps += 1

        job = Job(
            id=job_id,
            status=RenderStatus.PENDING,
            request=request,
            created_at=now,
            updated_at=now,
            total_steps=total_steps,
            message="Job created, waiting to start...",
        )

        async with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Created job {job_id} for project '{request.project_name}'")
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def list_jobs(self, status: Optional[RenderStatus] = None) -> List[Job]:
        """List all jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    async def update_job_status(
        self,
        job_id: str,
        status: RenderStatus,
        message: Optional[str] = None,
        error: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        job.status = status
        job.updated_at = datetime.utcnow()

        if status == RenderStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()

        if status in (RenderStatus.COMPLETE, RenderStatus.ERROR, RenderStatus.CANCELLED):
            job.completed_at = datetime.utcnow()

        if message:
            job.message = message
        if error:
            job.error = error
        if output_path:
            job.output_path = output_path

        logger.info(f"Job {job_id} status updated to {status}")
        return job

    async def update_job_progress(
        self,
        job_id: str,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        phase: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job progress."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        job.update_progress(current_step, total_steps, phase, message)

        # Trigger progress callback if set
        if self._on_progress:
            try:
                await self._on_progress(job)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

        return job

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Returns:
            True if job was cancelled, False otherwise.
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status not in (RenderStatus.PENDING, RenderStatus.RUNNING):
            return False

        # Cancel the asyncio task if running
        if job.task and not job.task.done():
            job.task.cancel()

        job.status = RenderStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.message = "Job cancelled by user"

        logger.info(f"Job {job_id} cancelled")
        return True

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job (only if not running)."""
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status == RenderStatus.RUNNING:
            return False

        async with self._lock:
            del self._jobs[job_id]

        logger.info(f"Job {job_id} deleted")
        return True

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed jobs.

        Args:
            max_age_hours: Maximum age of completed jobs to keep.

        Returns:
            Number of jobs removed.
        """
        now = datetime.utcnow()
        removed = 0

        async with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in (RenderStatus.COMPLETE, RenderStatus.ERROR, RenderStatus.CANCELLED):
                    if job.completed_at:
                        age_hours = (now - job.completed_at).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old jobs")

        return removed

    def get_running_count(self) -> int:
        """Get count of currently running jobs."""
        return sum(1 for j in self._jobs.values() if j.status == RenderStatus.RUNNING)

    def can_start_job(self) -> bool:
        """Check if a new job can be started."""
        return self.get_running_count() < self._max_concurrent


# Global job manager instance
job_manager = JobManager()
