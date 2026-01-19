"""
Render Service
Async wrapper around the StarStitchPipeline for non-blocking execution.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main import StarStitchPipeline
from .job_manager import job_manager, Job
from .websocket_manager import ws_manager
from ..models.render import RenderStatus
from ..models.progress import ProgressEvent

logger = logging.getLogger(__name__)


class RenderService:
    """
    Service for executing render jobs asynchronously.

    Wraps the synchronous StarStitchPipeline in asyncio.to_thread()
    and broadcasts progress updates via WebSocket.
    """

    def __init__(self):
        """Initialize the render service."""
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    async def execute_job(self, job_id: str) -> None:
        """
        Execute a render job asynchronously.

        Args:
            job_id: The ID of the job to execute.
        """
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Store the event loop for sync callbacks
        self._event_loop = asyncio.get_running_loop()

        # Update job status to running
        await job_manager.update_job_status(
            job_id,
            RenderStatus.RUNNING,
            message="Starting render pipeline...",
        )

        # Broadcast job started event
        event = ProgressEvent.job_started(
            job_id,
            total_steps=job.total_steps,
            project_name=job.request.project_name,
        )
        await ws_manager.broadcast(job_id, event)

        try:
            # Build config from request
            config = self._build_config(job)

            # Create progress callback that broadcasts to WebSocket
            step_counter = {"current": 0}

            def on_progress(message: str):
                """Progress callback that broadcasts to WebSocket."""
                nonlocal step_counter

                # Increment step counter for certain messages
                if any(x in message for x in ["Generating [", "Creating morph [", "Concatenating"]):
                    step_counter["current"] += 1

                # Create progress event from pipeline message
                event = ProgressEvent.from_pipeline_message(
                    job_id=job_id,
                    message=message,
                    current_step=step_counter["current"],
                    total_steps=job.total_steps,
                )

                # Update job state
                asyncio.run_coroutine_threadsafe(
                    job_manager.update_job_progress(
                        job_id,
                        current_step=step_counter["current"],
                        phase=event.phase,
                        message=message,
                    ),
                    self._event_loop,
                )

                # Broadcast to WebSocket
                ws_manager.broadcast_sync(job_id, event, self._event_loop)

                # Also log
                logger.info(f"[{job_id}] {message}")

            # Create pipeline with progress callback
            pipeline = StarStitchPipeline(
                config=config,
                on_progress=on_progress,
            )

            # Run the blocking pipeline in a thread pool
            logger.info(f"Starting pipeline execution for job {job_id}")
            output_path = await asyncio.to_thread(pipeline.run)

            # Update job as complete
            output_str = str(output_path) if output_path else None
            await job_manager.update_job_status(
                job_id,
                RenderStatus.COMPLETE,
                message="Render complete!",
                output_path=output_str,
            )

            # Calculate elapsed time
            job = await job_manager.get_job(job_id)
            elapsed = job.elapsed_seconds if job else 0

            # Broadcast completion
            event = ProgressEvent.job_completed(
                job_id,
                output_path=output_str or "",
                elapsed_seconds=elapsed,
            )
            await ws_manager.broadcast(job_id, event)

            logger.info(f"Job {job_id} completed successfully: {output_path}")

        except asyncio.CancelledError:
            # Job was cancelled
            logger.info(f"Job {job_id} was cancelled")
            await job_manager.update_job_status(
                job_id,
                RenderStatus.CANCELLED,
                message="Render cancelled",
            )

            event = ProgressEvent(
                type=ProgressEvent.JOB_CANCELLED,
                job_id=job_id,
                timestamp=datetime.utcnow(),
                message="Render cancelled",
            )
            await ws_manager.broadcast(job_id, event)

        except Exception as e:
            # Job failed
            error_msg = str(e)
            logger.error(f"Job {job_id} failed: {error_msg}")

            await job_manager.update_job_status(
                job_id,
                RenderStatus.ERROR,
                message=f"Render failed: {error_msg}",
                error=error_msg,
            )

            event = ProgressEvent.job_failed(job_id, error_msg)
            await ws_manager.broadcast(job_id, event)

    def _build_config(self, job: Job) -> dict:
        """
        Build a config dictionary from a job request.

        Args:
            job: The job to build config for.

        Returns:
            Configuration dictionary for StarStitchPipeline.
        """
        request = job.request

        # Convert Pydantic models to dicts
        settings = request.settings.model_dump()
        global_scene = request.global_scene.model_dump()
        audio = request.audio.model_dump()
        sequence = [s.model_dump() for s in request.sequence]

        config = {
            "project_name": request.project_name,
            "output_folder": request.output_folder,
            "settings": {
                "aspect_ratio": settings["aspect_ratio"],
                "transition_duration_sec": settings["transition_duration_sec"],
                "image_model": settings["image_model"],
                "video_model": settings["video_model"],
                "variants": settings.get("variants", []),
            },
            "global_scene": {
                "location_prompt": global_scene["location_prompt"],
                "negative_prompt": global_scene["negative_prompt"],
            },
            "audio": {
                "enabled": audio["enabled"],
                "audio_path": audio["audio_path"],
                "volume": audio["volume"],
                "fade_in_sec": audio["fade_in_sec"],
                "fade_out_sec": audio["fade_out_sec"],
                "loop": audio["loop"],
                "normalize": audio["normalize"],
            },
            "sequence": sequence,
        }

        return config


# Global render service instance
render_service = RenderService()


async def execute_render_job(job_id: str) -> None:
    """
    Execute a render job (entry point for background tasks).

    Args:
        job_id: The ID of the job to execute.
    """
    await render_service.execute_job(job_id)
