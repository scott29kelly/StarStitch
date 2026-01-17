"""
State management for StarStitch.
Handles progress tracking and resume capability.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum


class StepStatus(str, Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepState:
    """State of a single pipeline step."""

    step_id: str
    step_type: str  # "anchor", "target", "morph", "lastframe", "concat"
    subject_name: str
    index: int
    status: StepStatus = StepStatus.PENDING
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepState":
        """Create from dictionary."""
        data["status"] = StepStatus(data["status"])
        return cls(**data)


@dataclass
class PipelineState:
    """Complete state of the pipeline."""

    project_name: str
    render_folder: str
    config_hash: str  # Hash of config for validation
    created_at: str
    last_updated: str
    current_start_frame: Optional[str] = None  # Path to current start frame
    current_step_index: int = 0
    total_steps: int = 0
    steps: List[StepState] = field(default_factory=list)
    is_completed: bool = False
    final_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_name": self.project_name,
            "render_folder": self.render_folder,
            "config_hash": self.config_hash,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "current_start_frame": self.current_start_frame,
            "current_step_index": self.current_step_index,
            "total_steps": self.total_steps,
            "steps": [step.to_dict() for step in self.steps],
            "is_completed": self.is_completed,
            "final_output": self.final_output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState":
        """Create from dictionary."""
        steps = [StepState.from_dict(s) for s in data.get("steps", [])]
        return cls(
            project_name=data["project_name"],
            render_folder=data["render_folder"],
            config_hash=data["config_hash"],
            created_at=data["created_at"],
            last_updated=data["last_updated"],
            current_start_frame=data.get("current_start_frame"),
            current_step_index=data.get("current_step_index", 0),
            total_steps=data.get("total_steps", 0),
            steps=steps,
            is_completed=data.get("is_completed", False),
            final_output=data.get("final_output"),
        )


class StateManager:
    """
    Manages pipeline state for progress tracking and resume capability.
    
    Persists state to a JSON file in the render folder, allowing
    the pipeline to resume from where it left off after a crash.
    """

    def __init__(
        self,
        state_file_path: Path,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the state manager.
        
        Args:
            state_file_path: Path to the state.json file.
            logger: Optional logger instance.
        """
        self.state_file_path = state_file_path
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._state: Optional[PipelineState] = None

    @property
    def state(self) -> PipelineState:
        """Get the current pipeline state."""
        if self._state is None:
            raise RuntimeError("State not initialized. Call initialize() or load() first.")
        return self._state

    def initialize(
        self,
        project_name: str,
        render_folder: Path,
        config_hash: str,
        sequence_length: int,
    ) -> PipelineState:
        """
        Initialize a new pipeline state.
        
        Args:
            project_name: Name of the project.
            render_folder: Path to the render output folder.
            config_hash: Hash of the configuration for validation.
            sequence_length: Number of subjects in the sequence.
            
        Returns:
            The initialized pipeline state.
        """
        now = datetime.now().isoformat()

        # Calculate total steps:
        # 1 anchor image + (n-1) * 3 steps per person (target, morph, lastframe) + 1 concat
        # For n subjects: 1 + (n-1)*3 + 1 = 3n - 1
        total_steps = 1 + (sequence_length - 1) * 3 + 1

        self._state = PipelineState(
            project_name=project_name,
            render_folder=str(render_folder),
            config_hash=config_hash,
            created_at=now,
            last_updated=now,
            total_steps=total_steps,
        )

        self.save()
        self.logger.info(f"Initialized new pipeline state with {total_steps} steps")

        return self._state

    def load(self) -> PipelineState:
        """
        Load existing state from file.
        
        Returns:
            The loaded pipeline state.
            
        Raises:
            FileNotFoundError: If state file doesn't exist.
            ValueError: If state file is invalid.
        """
        if not self.state_file_path.exists():
            raise FileNotFoundError(f"State file not found: {self.state_file_path}")

        try:
            with open(self.state_file_path, "r") as f:
                data = json.load(f)

            self._state = PipelineState.from_dict(data)
            self.logger.info(f"Loaded pipeline state from {self.state_file_path}")
            self.logger.info(
                f"Progress: {self.get_completed_steps()}/{self._state.total_steps} steps completed"
            )

            return self._state

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid state file format: {e}")

    def save(self) -> None:
        """Save current state to file."""
        if self._state is None:
            return

        self._state.last_updated = datetime.now().isoformat()

        # Ensure parent directory exists
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.state_file_path, "w") as f:
            json.dump(self._state.to_dict(), f, indent=2)

        self.logger.debug(f"State saved to {self.state_file_path}")

    def add_step(
        self,
        step_id: str,
        step_type: str,
        subject_name: str,
        index: int,
    ) -> StepState:
        """
        Add a new step to the state.
        
        Args:
            step_id: Unique identifier for the step.
            step_type: Type of step (anchor, target, morph, lastframe, concat).
            subject_name: Name of the subject for this step.
            index: Sequence index.
            
        Returns:
            The created step state.
        """
        step = StepState(
            step_id=step_id,
            step_type=step_type,
            subject_name=subject_name,
            index=index,
        )
        self.state.steps.append(step)
        self.save()
        return step

    def start_step(self, step_id: str) -> None:
        """
        Mark a step as in progress.
        
        Args:
            step_id: The step identifier.
        """
        step = self._find_step(step_id)
        if step:
            step.status = StepStatus.IN_PROGRESS
            step.started_at = datetime.now().isoformat()
            self.save()

    def complete_step(
        self,
        step_id: str,
        output_path: Optional[Path] = None,
        duration: Optional[float] = None,
    ) -> None:
        """
        Mark a step as completed.
        
        Args:
            step_id: The step identifier.
            output_path: Optional path to the step's output file.
            duration: Optional duration in seconds.
        """
        step = self._find_step(step_id)
        if step:
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()
            if output_path:
                step.output_path = str(output_path)
            if duration:
                step.duration_seconds = duration
            self.state.current_step_index += 1
            self.save()

    def fail_step(self, step_id: str, error_message: str) -> None:
        """
        Mark a step as failed.
        
        Args:
            step_id: The step identifier.
            error_message: Description of the error.
        """
        step = self._find_step(step_id)
        if step:
            step.status = StepStatus.FAILED
            step.error_message = error_message
            step.completed_at = datetime.now().isoformat()
            self.save()

    def update_current_start_frame(self, frame_path: Path) -> None:
        """
        Update the current start frame for the next iteration.
        
        This is critical for the "glitch fix" - we use the extracted
        last frame as the start of the next morph, not the original target.
        
        Args:
            frame_path: Path to the current start frame image.
        """
        self.state.current_start_frame = str(frame_path)
        self.save()

    def get_current_start_frame(self) -> Optional[Path]:
        """
        Get the current start frame path.
        
        Returns:
            Path to the current start frame, or None if not set.
        """
        if self.state.current_start_frame:
            return Path(self.state.current_start_frame)
        return None

    def mark_completed(self, final_output: Path) -> None:
        """
        Mark the entire pipeline as completed.
        
        Args:
            final_output: Path to the final output video.
        """
        self.state.is_completed = True
        self.state.final_output = str(final_output)
        self.save()
        self.logger.info("Pipeline marked as completed!")

    def get_completed_steps(self) -> int:
        """Get the number of completed steps."""
        return sum(1 for s in self.state.steps if s.status == StepStatus.COMPLETED)

    def get_pending_steps(self) -> List[StepState]:
        """Get all pending steps."""
        return [s for s in self.state.steps if s.status == StepStatus.PENDING]

    def get_last_completed_step(self) -> Optional[StepState]:
        """Get the most recently completed step."""
        completed = [s for s in self.state.steps if s.status == StepStatus.COMPLETED]
        return completed[-1] if completed else None

    def is_step_completed(self, step_id: str) -> bool:
        """Check if a specific step is completed."""
        step = self._find_step(step_id)
        return step is not None and step.status == StepStatus.COMPLETED

    def get_resume_point(self) -> Optional[int]:
        """
        Determine where to resume from after a crash.
        
        Returns:
            The index of the first incomplete step, or None if all complete.
        """
        for i, step in enumerate(self.state.steps):
            if step.status != StepStatus.COMPLETED:
                return i
        return None

    def _find_step(self, step_id: str) -> Optional[StepState]:
        """Find a step by its ID."""
        for step in self.state.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_progress_summary(self) -> str:
        """Get a human-readable progress summary."""
        completed = self.get_completed_steps()
        total = self.state.total_steps
        percentage = (completed / total * 100) if total > 0 else 0
        return f"{completed}/{total} steps completed ({percentage:.0f}%)"
