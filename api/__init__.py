"""
StarStitch API Backend
RESTful API for programmatic access and React frontend integration.
"""

from .main import app
from .models import (
    RenderRequest,
    RenderResponse,
    RenderStatus,
    RenderProgress,
    TemplateInfo,
    JobState,
)
from .job_queue import JobQueue, job_queue

__all__ = [
    "app",
    "RenderRequest",
    "RenderResponse", 
    "RenderStatus",
    "RenderProgress",
    "TemplateInfo",
    "JobState",
    "JobQueue",
    "job_queue",
]
