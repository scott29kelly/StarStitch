"""
Render Models
Pydantic models for render requests and status tracking.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RenderStatus(str, Enum):
    """Render job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class SubjectConfig(BaseModel):
    """Configuration for a single subject in the sequence."""
    id: Optional[str] = None
    name: str
    visual_prompt: str

    class Config:
        extra = "allow"


class GlobalSceneConfig(BaseModel):
    """Global scene configuration applied to all images."""
    location_prompt: str = ""
    negative_prompt: str = ""


class AudioConfig(BaseModel):
    """Audio track configuration."""
    enabled: bool = False
    audio_path: str = ""
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    fade_in_sec: float = Field(default=1.0, ge=0.0)
    fade_out_sec: float = Field(default=2.0, ge=0.0)
    loop: bool = True
    normalize: bool = True


class SettingsConfig(BaseModel):
    """Render settings configuration."""
    aspect_ratio: str = "9:16"
    transition_duration_sec: int = Field(default=5, ge=2, le=10)
    image_model: str = "black-forest-labs/flux-1.1-pro"
    video_model: str = "fal-ai/kling-video/v1.6/pro/image-to-video"
    variants: List[str] = Field(default_factory=list)


class RenderRequest(BaseModel):
    """Request to start a new render job."""
    project_name: str = Field(..., min_length=1, max_length=100)
    output_folder: str = "renders"
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    global_scene: GlobalSceneConfig = Field(default_factory=GlobalSceneConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    sequence: List[SubjectConfig] = Field(..., min_length=2)

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "eiffel_tower_stars",
                "output_folder": "renders",
                "settings": {
                    "aspect_ratio": "9:16",
                    "transition_duration_sec": 5,
                },
                "global_scene": {
                    "location_prompt": "taking a selfie at the Eiffel Tower, golden hour lighting",
                    "negative_prompt": "blurry, distorted",
                },
                "sequence": [
                    {"name": "Tourist", "visual_prompt": "A friendly tourist smiling"},
                    {"name": "Artist", "visual_prompt": "A creative artist with paint-stained clothes"},
                ],
            }
        }


class RenderResponse(BaseModel):
    """Response for a render job."""
    id: str
    status: RenderStatus
    project_name: str
    created_at: datetime
    updated_at: datetime
    current_step: int = 0
    total_steps: int = 0
    progress_percent: float = 0.0
    current_phase: str = ""
    message: str = ""
    output_path: Optional[str] = None
    error: Optional[str] = None
    elapsed_seconds: float = 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "id": "render_abc123",
                "status": "running",
                "project_name": "eiffel_tower_stars",
                "created_at": "2026-01-18T12:00:00Z",
                "updated_at": "2026-01-18T12:05:00Z",
                "current_step": 3,
                "total_steps": 10,
                "progress_percent": 30.0,
                "current_phase": "image_generation",
                "message": "Generating image for Artist...",
            }
        }


class RenderListResponse(BaseModel):
    """Response for listing render jobs."""
    renders: List[RenderResponse]
    total: int
