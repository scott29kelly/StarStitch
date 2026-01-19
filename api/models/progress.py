"""
Progress Event Models
Models for real-time progress streaming via WebSocket.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ProgressEventType(str, Enum):
    """Types of progress events."""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

    # Job lifecycle events
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"

    # Step events
    STEP_STARTED = "step_started"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETED = "step_completed"

    # Generic progress
    PROGRESS = "progress"
    LOG = "log"
    ERROR = "error"


class ProgressEvent(BaseModel):
    """A progress event sent via WebSocket."""
    type: ProgressEventType
    job_id: str
    timestamp: datetime

    # Progress tracking
    current_step: int = 0
    total_steps: int = 0
    progress_percent: float = 0.0

    # Context
    phase: Optional[str] = None
    subject: Optional[str] = None
    message: str = ""

    # Additional data
    data: Dict[str, Any] = {}

    @classmethod
    def connected(cls, job_id: str) -> "ProgressEvent":
        """Create a connected event."""
        return cls(
            type=ProgressEventType.CONNECTED,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            message="Connected to progress stream",
        )

    @classmethod
    def job_started(
        cls,
        job_id: str,
        total_steps: int,
        project_name: str = "",
    ) -> "ProgressEvent":
        """Create a job started event."""
        return cls(
            type=ProgressEventType.JOB_STARTED,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            total_steps=total_steps,
            message=f"Started render job: {project_name}",
            data={"project_name": project_name},
        )

    @classmethod
    def job_completed(
        cls,
        job_id: str,
        output_path: str,
        elapsed_seconds: float = 0,
    ) -> "ProgressEvent":
        """Create a job completed event."""
        return cls(
            type=ProgressEventType.JOB_COMPLETED,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            progress_percent=100.0,
            message="Render complete!",
            data={"output_path": output_path, "elapsed_seconds": elapsed_seconds},
        )

    @classmethod
    def job_failed(cls, job_id: str, error: str) -> "ProgressEvent":
        """Create a job failed event."""
        return cls(
            type=ProgressEventType.JOB_FAILED,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            message=f"Render failed: {error}",
            data={"error": error},
        )

    @classmethod
    def progress(
        cls,
        job_id: str,
        current_step: int,
        total_steps: int,
        message: str,
        phase: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> "ProgressEvent":
        """Create a generic progress event."""
        progress_percent = (current_step / total_steps * 100) if total_steps > 0 else 0
        return cls(
            type=ProgressEventType.PROGRESS,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            current_step=current_step,
            total_steps=total_steps,
            progress_percent=progress_percent,
            phase=phase,
            subject=subject,
            message=message,
        )

    @classmethod
    def log(cls, job_id: str, message: str) -> "ProgressEvent":
        """Create a log event."""
        return cls(
            type=ProgressEventType.LOG,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            message=message,
        )

    @classmethod
    def from_pipeline_message(cls, job_id: str, message: str, current_step: int = 0, total_steps: int = 0) -> "ProgressEvent":
        """
        Parse a pipeline progress message into a ProgressEvent.

        The StarStitchPipeline sends messages like:
        - "=== Phase 1: Generating Subject Images ==="
        - "Generating [1/5]: Tourist"
        - "Creating morph [1/4]: Tourist -> Artist"
        """
        phase = None
        subject = None
        event_type = ProgressEventType.PROGRESS

        # Detect phase changes
        if "===" in message:
            event_type = ProgressEventType.PHASE_STARTED
            if "Generating Subject Images" in message:
                phase = "image_generation"
            elif "Generating Morph Transitions" in message:
                phase = "video_generation"
            elif "Creating Final Video" in message:
                phase = "concatenation"
            elif "Adding Audio" in message:
                phase = "audio"
            elif "Generating Variants" in message:
                phase = "variants"

        # Detect step progress
        elif "Generating [" in message:
            phase = "image_generation"
            event_type = ProgressEventType.STEP_PROGRESS
            # Extract subject name after the colon
            if ": " in message:
                subject = message.split(": ", 1)[1]

        elif "Creating morph [" in message:
            phase = "video_generation"
            event_type = ProgressEventType.STEP_PROGRESS
            if ": " in message:
                subject = message.split(": ", 1)[1]

        elif "Pipeline complete" in message:
            event_type = ProgressEventType.JOB_COMPLETED

        elif "Pipeline failed" in message or "Error" in message.lower():
            event_type = ProgressEventType.ERROR

        progress_percent = (current_step / total_steps * 100) if total_steps > 0 else 0

        return cls(
            type=event_type,
            job_id=job_id,
            timestamp=datetime.utcnow(),
            current_step=current_step,
            total_steps=total_steps,
            progress_percent=progress_percent,
            phase=phase,
            subject=subject,
            message=message,
        )
