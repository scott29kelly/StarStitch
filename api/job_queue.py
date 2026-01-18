"""
Job Queue
Background task processing for render jobs.
Uses asyncio for in-memory queue management.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .models import JobState, RenderProgress, RenderStatus

logger = logging.getLogger(__name__)


@dataclass
class RenderJob:
    """A render job in the queue."""
    job_id: str
    config: Dict[str, Any]
    state: JobState = JobState.PENDING
    progress: Optional[RenderProgress] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    variant_paths: Dict[str, str] = field(default_factory=dict)
    error_message: Optional[str] = None
    render_dir: Optional[str] = None
    _cancel_requested: bool = False

    def to_status(self) -> RenderStatus:
        """Convert to RenderStatus response."""
        return RenderStatus(
            job_id=self.job_id,
            state=self.state,
            progress=self.progress,
            config=self.config,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            output_path=self.output_path,
            variant_paths=self.variant_paths,
            error_message=self.error_message,
            render_dir=self.render_dir,
        )

    @property
    def project_name(self) -> str:
        """Get project name from config."""
        return self.config.get("project_name", "unnamed")

    @property
    def subjects_count(self) -> int:
        """Get number of subjects from config."""
        return len(self.config.get("sequence", []))


class JobQueue:
    """
    In-memory job queue with background processing.
    
    Features:
    - Configurable concurrency (default: 1 job at a time)
    - Job state tracking (pending, running, complete, failed, cancelled)
    - WebSocket notification callbacks
    - Job history retention
    """

    def __init__(self, max_concurrent: int = 1, max_history: int = 100):
        """
        Initialize the job queue.
        
        Args:
            max_concurrent: Maximum concurrent jobs (default: 1)
            max_history: Maximum completed jobs to retain in history
        """
        self.max_concurrent = max_concurrent
        self.max_history = max_history
        
        # Job storage
        self._jobs: Dict[str, RenderJob] = {}
        self._pending_queue: asyncio.Queue[str] = asyncio.Queue()
        self._running_jobs: Set[str] = set()
        
        # Callbacks for WebSocket notifications
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        
        # Worker task
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Pipeline factory (set by main app)
        self._pipeline_factory: Optional[Callable] = None
        
        logger.info(f"JobQueue initialized with max_concurrent={max_concurrent}")

    def set_pipeline_factory(self, factory: Callable):
        """Set the pipeline factory function."""
        self._pipeline_factory = factory

    async def start(self):
        """Start the job queue worker."""
        if self._worker_task is None:
            self._shutdown_event.clear()
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Job queue worker started")

    async def stop(self):
        """Stop the job queue worker gracefully."""
        self._shutdown_event.set()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("Job queue worker stopped")

    def create_job(self, config: Dict[str, Any]) -> RenderJob:
        """
        Create a new render job.
        
        Args:
            config: Render configuration dictionary.
            
        Returns:
            The created RenderJob.
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        job = RenderJob(
            job_id=job_id,
            config=config,
            state=JobState.PENDING,
        )
        
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} for project '{job.project_name}'")
        
        return job

    async def enqueue(self, job_id: str) -> bool:
        """
        Add a job to the processing queue.
        
        Args:
            job_id: The job identifier.
            
        Returns:
            True if enqueued successfully.
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if job.state != JobState.PENDING:
            logger.warning(f"Job {job_id} is not pending (state: {job.state})")
            return False
        
        await self._pending_queue.put(job_id)
        logger.info(f"Job {job_id} enqueued, queue size: {self._pending_queue.qsize()}")
        
        return True

    def get_job(self, job_id: str) -> Optional[RenderJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[RenderStatus]:
        """Get job status as response model."""
        job = self._jobs.get(job_id)
        return job.to_status() if job else None

    def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        state_filter: Optional[JobState] = None,
    ) -> tuple[List[RenderJob], int]:
        """
        List jobs with pagination.
        
        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            state_filter: Optional state filter.
            
        Returns:
            Tuple of (jobs list, total count).
        """
        # Filter jobs
        jobs = list(self._jobs.values())
        if state_filter:
            jobs = [j for j in jobs if j.state == state_filter]
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        total = len(jobs)
        
        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        
        return jobs[start:end], total

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: The job identifier.
            
        Returns:
            True if cancellation was successful or already cancelled.
        """
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.state == JobState.CANCELLED:
            return True
        
        if job.state == JobState.COMPLETE:
            return False  # Can't cancel completed job
        
        job._cancel_requested = True
        
        if job.state == JobState.PENDING:
            job.state = JobState.CANCELLED
            job.completed_at = datetime.now()
            logger.info(f"Job {job_id} cancelled (was pending)")
        elif job.state == JobState.RUNNING:
            # Job will check _cancel_requested flag
            logger.info(f"Job {job_id} cancellation requested (running)")
        
        # Notify subscribers
        asyncio.create_task(self._notify_cancelled(job_id))
        
        return True

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from history.
        
        Args:
            job_id: The job identifier.
            
        Returns:
            True if deleted.
        """
        if job_id in self._jobs:
            job = self._jobs[job_id]
            if job.state == JobState.RUNNING:
                return False  # Can't delete running job
            del self._jobs[job_id]
            self._progress_callbacks.pop(job_id, None)
            return True
        return False

    def register_progress_callback(self, job_id: str, callback: Callable):
        """Register a callback for progress updates."""
        if job_id not in self._progress_callbacks:
            self._progress_callbacks[job_id] = []
        self._progress_callbacks[job_id].append(callback)

    def unregister_progress_callback(self, job_id: str, callback: Callable):
        """Unregister a progress callback."""
        if job_id in self._progress_callbacks:
            try:
                self._progress_callbacks[job_id].remove(callback)
            except ValueError:
                pass

    async def _notify_progress(self, job_id: str, progress: RenderProgress):
        """Notify all registered callbacks of progress."""
        callbacks = self._progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("progress", progress.model_dump())
                else:
                    callback("progress", progress.model_dump())
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    async def _notify_complete(self, job_id: str, output_path: str, variant_paths: Dict[str, str]):
        """Notify job completion."""
        callbacks = self._progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                data = {"output_path": output_path, "variant_paths": variant_paths}
                if asyncio.iscoroutinefunction(callback):
                    await callback("complete", data)
                else:
                    callback("complete", data)
            except Exception as e:
                logger.warning(f"Complete callback error: {e}")

    async def _notify_error(self, job_id: str, error: str):
        """Notify job error."""
        callbacks = self._progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("error", {"message": error})
                else:
                    callback("error", {"message": error})
            except Exception as e:
                logger.warning(f"Error callback error: {e}")

    async def _notify_cancelled(self, job_id: str):
        """Notify job cancellation."""
        callbacks = self._progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("cancelled", {})
                else:
                    callback("cancelled", {})
            except Exception as e:
                logger.warning(f"Cancelled callback error: {e}")

    async def _worker_loop(self):
        """Main worker loop that processes jobs from the queue."""
        logger.info("Worker loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for available slot
                while len(self._running_jobs) >= self.max_concurrent:
                    await asyncio.sleep(0.1)
                
                # Get next job from queue
                try:
                    job_id = await asyncio.wait_for(
                        self._pending_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                job = self._jobs.get(job_id)
                if not job or job.state != JobState.PENDING:
                    continue
                
                # Process job
                self._running_jobs.add(job_id)
                asyncio.create_task(self._process_job(job_id))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)
        
        logger.info("Worker loop stopped")

    async def _process_job(self, job_id: str):
        """Process a single render job."""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        job.state = JobState.RUNNING
        job.started_at = datetime.now()
        start_time = time.time()
        
        logger.info(f"Starting job {job_id}")
        
        try:
            # Check for pipeline factory
            if not self._pipeline_factory:
                raise RuntimeError("Pipeline factory not configured")
            
            # Calculate steps
            sequence = job.config.get("sequence", [])
            num_subjects = len(sequence)
            num_morphs = max(0, num_subjects - 1)
            variants = job.config.get("settings", {}).get("variants", [])
            audio_enabled = job.config.get("audio", {}).get("enabled", False)
            
            total_steps = num_subjects + num_morphs + (1 if variants else 0) + (1 if audio_enabled else 0) + 1
            
            current_step = 0
            
            def on_progress(message: str):
                """Progress callback from pipeline."""
                nonlocal current_step
                
                if job._cancel_requested:
                    raise asyncio.CancelledError("Job cancelled by user")
                
                elapsed = time.time() - start_time
                
                # Determine phase and update step
                phase = "initializing"
                if "image" in message.lower() or "generating" in message.lower():
                    phase = "images"
                    if "generating [" in message.lower():
                        current_step += 1
                elif "morph" in message.lower():
                    phase = "morphs"
                    if "creating morph" in message.lower():
                        current_step += 1
                elif "audio" in message.lower():
                    phase = "audio"
                    current_step += 1
                elif "variant" in message.lower():
                    phase = "variants"
                    current_step += 1
                elif "concatenat" in message.lower() or "final" in message.lower():
                    phase = "finalizing"
                    current_step += 1
                
                progress = RenderProgress(
                    step=min(current_step, total_steps),
                    total_steps=total_steps,
                    phase=phase,
                    message=message,
                    progress_percent=min((current_step / total_steps) * 100, 100),
                    elapsed_seconds=elapsed,
                    estimated_remaining_seconds=(elapsed / max(current_step, 1)) * (total_steps - current_step) if current_step > 0 else None,
                )
                
                job.progress = progress
                
                # Notify via asyncio
                asyncio.create_task(self._notify_progress(job_id, progress))
            
            # Run pipeline in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_pipeline_sync,
                job.config,
                on_progress,
            )
            
            output_path, variant_paths, render_dir = result
            
            job.state = JobState.COMPLETE
            job.completed_at = datetime.now()
            job.output_path = str(output_path) if output_path else None
            job.variant_paths = variant_paths or {}
            job.render_dir = str(render_dir) if render_dir else None
            
            # Final progress
            job.progress = RenderProgress(
                step=total_steps,
                total_steps=total_steps,
                phase="complete",
                message="Render complete!",
                progress_percent=100,
                elapsed_seconds=time.time() - start_time,
            )
            
            logger.info(f"Job {job_id} completed: {output_path}")
            await self._notify_complete(job_id, str(output_path), variant_paths or {})
            
        except asyncio.CancelledError:
            job.state = JobState.CANCELLED
            job.completed_at = datetime.now()
            job.error_message = "Job cancelled by user"
            logger.info(f"Job {job_id} cancelled")
            await self._notify_cancelled(job_id)
            
        except Exception as e:
            job.state = JobState.FAILED
            job.completed_at = datetime.now()
            job.error_message = str(e)
            logger.error(f"Job {job_id} failed: {e}")
            await self._notify_error(job_id, str(e))
        
        finally:
            self._running_jobs.discard(job_id)
            self._cleanup_old_jobs()

    def _run_pipeline_sync(
        self,
        config: Dict[str, Any],
        on_progress: Callable[[str], None],
    ) -> tuple[Optional[Path], Optional[Dict[str, str]], Optional[Path]]:
        """
        Run the StarStitch pipeline synchronously.
        
        This is called from a thread pool executor.
        """
        if not self._pipeline_factory:
            raise RuntimeError("Pipeline factory not configured")
        
        # Import here to avoid circular imports
        from main import StarStitchPipeline
        
        # Get variants from config
        variants = config.get("settings", {}).get("variants", [])
        
        pipeline = StarStitchPipeline(
            config=config,
            on_progress=on_progress,
            variants_override=variants if variants else None,
        )
        
        output_path = pipeline.run()
        
        # Get variant paths if generated
        variant_paths = {}
        if variants and pipeline.file_manager.render_dir:
            variants_dir = pipeline.file_manager.render_dir / "variants"
            if variants_dir.exists():
                for ratio in variants:
                    ratio_safe = ratio.replace(":", "x")
                    variant_file = variants_dir / f"variant_{ratio_safe}.mp4"
                    if variant_file.exists():
                        variant_paths[ratio] = str(variant_file)
        
        return output_path, variant_paths, pipeline.file_manager.render_dir

    def _cleanup_old_jobs(self):
        """Remove old completed jobs beyond max_history."""
        completed_jobs = [
            j for j in self._jobs.values()
            if j.state in (JobState.COMPLETE, JobState.FAILED, JobState.CANCELLED)
        ]
        
        if len(completed_jobs) > self.max_history:
            # Sort by completion time
            completed_jobs.sort(key=lambda j: j.completed_at or j.created_at)
            
            # Remove oldest
            to_remove = len(completed_jobs) - self.max_history
            for job in completed_jobs[:to_remove]:
                del self._jobs[job.job_id]
                self._progress_callbacks.pop(job.job_id, None)


# Global job queue instance
job_queue = JobQueue()
