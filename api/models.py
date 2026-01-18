"""
API Models and Schemas
Pydantic models for request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobState(str, Enum):
    """State of a render job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubjectSchema(BaseModel):
    """A subject in the morph sequence."""
    id: str = Field(..., description="Unique identifier for the subject")
    name: str = Field(..., description="Display name of the subject")
    visual_prompt: str = Field(..., description="Visual description prompt")


class SettingsSchema(BaseModel):
    """Generation settings."""
    aspect_ratio: str = Field(default="9:16", description="Output aspect ratio")
    transition_duration_sec: int = Field(default=5, ge=2, le=10, description="Duration of each transition")
    image_model: str = Field(default="black-forest-labs/flux-1.1-pro", description="Image generation model")
    video_model: str = Field(default="fal-ai/kling-video/v1.6/pro/image-to-video", description="Video generation model")
    variants: List[str] = Field(default_factory=list, description="Output variant aspect ratios")


class GlobalSceneSchema(BaseModel):
    """Global scene settings."""
    location_prompt: str = Field(..., description="Location/scene description")
    negative_prompt: str = Field(default="blurry, distorted, cartoon, low quality", description="Negative prompt")


class AudioSchema(BaseModel):
    """Audio configuration."""
    enabled: bool = Field(default=False, description="Enable audio track")
    audio_path: str = Field(default="", description="Path to audio file")
    volume: float = Field(default=0.8, ge=0.0, le=1.0, description="Audio volume")
    fade_in_sec: float = Field(default=1.0, ge=0.0, description="Fade in duration")
    fade_out_sec: float = Field(default=2.0, ge=0.0, description="Fade out duration")
    loop: bool = Field(default=True, description="Loop audio if shorter than video")
    normalize: bool = Field(default=True, description="Normalize audio volume")


class RenderRequest(BaseModel):
    """Request body for starting a new render."""
    project_name: str = Field(..., min_length=1, description="Project name")
    output_folder: str = Field(default="renders", description="Output folder path")
    settings: SettingsSchema = Field(default_factory=SettingsSchema)
    global_scene: GlobalSceneSchema
    sequence: List[SubjectSchema] = Field(..., min_length=2, description="At least 2 subjects required")
    audio: Optional[AudioSchema] = Field(default=None, description="Audio configuration")
    template_name: Optional[str] = Field(default=None, description="Template to use as base")

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "eiffel_tower_stars",
                "output_folder": "renders",
                "settings": {
                    "aspect_ratio": "9:16",
                    "transition_duration_sec": 5,
                    "image_model": "black-forest-labs/flux-1.1-pro",
                    "video_model": "fal-ai/kling-video/v1.6/pro/image-to-video",
                    "variants": []
                },
                "global_scene": {
                    "location_prompt": "taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic",
                    "negative_prompt": "blurry, distorted, cartoon, low quality"
                },
                "sequence": [
                    {"id": "anchor", "name": "Tourist", "visual_prompt": "A friendly tourist in casual clothes"},
                    {"id": "subj_1", "name": "Celebrity", "visual_prompt": "A famous movie star, well-dressed"}
                ]
            }
        }


class RenderProgress(BaseModel):
    """Real-time progress update for a render job."""
    step: int = Field(..., description="Current step number")
    total_steps: int = Field(..., description="Total number of steps")
    phase: str = Field(..., description="Current phase (images, morphs, audio, variants)")
    message: str = Field(..., description="Human-readable progress message")
    progress_percent: float = Field(..., ge=0, le=100, description="Overall progress percentage")
    current_subject: Optional[str] = Field(default=None, description="Currently processing subject")
    elapsed_seconds: float = Field(default=0, description="Elapsed time in seconds")
    estimated_remaining_seconds: Optional[float] = Field(default=None, description="Estimated time remaining")


class RenderStatus(BaseModel):
    """Status response for a render job."""
    job_id: str = Field(..., description="Unique job identifier")
    state: JobState = Field(..., description="Current job state")
    progress: Optional[RenderProgress] = Field(default=None, description="Progress details if running")
    config: Dict[str, Any] = Field(default_factory=dict, description="Render configuration")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")
    output_path: Optional[str] = Field(default=None, description="Path to output video")
    variant_paths: Dict[str, str] = Field(default_factory=dict, description="Paths to variant videos")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    render_dir: Optional[str] = Field(default=None, description="Render directory path")


class RenderResponse(BaseModel):
    """Response after starting a render."""
    job_id: str = Field(..., description="Unique job identifier")
    message: str = Field(..., description="Status message")
    state: JobState = Field(..., description="Initial job state")
    websocket_url: str = Field(..., description="WebSocket URL for progress updates")


class RenderListItem(BaseModel):
    """Summary item for render list."""
    job_id: str
    project_name: str
    state: JobState
    created_at: datetime
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    subjects_count: int
    progress_percent: float = 0


class RenderListResponse(BaseModel):
    """Response for listing renders."""
    renders: List[RenderListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class TemplateInfo(BaseModel):
    """Template information."""
    name: str = Field(..., description="Template unique name")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    tags: List[str] = Field(default_factory=list, description="Search tags")
    thumbnail: Optional[str] = Field(default=None, description="Thumbnail URL")
    author: str = Field(default="StarStitch", description="Template author")
    version: str = Field(default="1.0", description="Template version")


class TemplateListResponse(BaseModel):
    """Response for listing templates."""
    templates: List[TemplateInfo]
    categories: List[Dict[str, Any]]
    total: int


class TemplateDetailResponse(BaseModel):
    """Detailed template response with base config."""
    info: TemplateInfo
    base_config: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str = Field(..., description="Message type: progress, error, complete, cancelled")
    job_id: str = Field(..., description="Job identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
