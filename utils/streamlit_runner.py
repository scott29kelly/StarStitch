"""
Streamlit Pipeline Runner
Thread-safe wrapper for StarStitchPipeline that communicates via shared state.
"""

import threading
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class PipelineProgress:
    """Thread-safe container for pipeline progress state."""
    status: PipelineStatus = PipelineStatus.IDLE
    current_step: int = 0
    total_steps: int = 0
    current_phase: str = ""
    current_action: str = ""
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    final_video_path: Optional[Path] = None
    variant_paths: Dict[str, Path] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    render_dir: Optional[Path] = None

    def add_log(self, message: str) -> None:
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        # Keep only last 100 logs to prevent memory bloat
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]


class PipelineRunner:
    """
    Thread-safe pipeline runner for Streamlit integration.

    Manages a background thread that runs the StarStitchPipeline,
    communicating progress via a shared PipelineProgress object.

    Usage in Streamlit:
        if "runner" not in st.session_state:
            st.session_state.runner = PipelineRunner()

        runner = st.session_state.runner

        if st.button("Start"):
            runner.start(config)

        if runner.is_running():
            progress = runner.get_progress()
            st.progress(progress.current_step / progress.total_steps)
            time.sleep(0.5)
            st.rerun()
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._progress = PipelineProgress()
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()

    def start(self, config: Dict[str, Any]) -> bool:
        """
        Start the pipeline in a background thread.

        Args:
            config: The StarStitch configuration dictionary.

        Returns:
            True if started successfully, False if already running.
        """
        if self.is_running():
            return False

        # Reset state
        with self._lock:
            self._progress = PipelineProgress()
            self._progress.status = PipelineStatus.RUNNING
            self._progress.started_at = datetime.now()

        self._cancel_event.clear()

        # Start background thread
        self._thread = threading.Thread(
            target=self._run_pipeline,
            args=(config,),
            daemon=True
        )
        self._thread.start()

        return True

    def _run_pipeline(self, config: Dict[str, Any]) -> None:
        """Execute the pipeline in the background thread."""
        try:
            # Import here to avoid circular imports
            import sys
            from pathlib import Path

            # Ensure the project root is in the path
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from main import StarStitchPipeline

            # Create pipeline with progress callback
            pipeline = StarStitchPipeline(
                config=config,
                on_progress=self._on_progress
            )

            # Run the pipeline
            final_path = pipeline.run()

            # Success!
            with self._lock:
                self._progress.status = PipelineStatus.COMPLETE
                self._progress.final_video_path = final_path
                self._progress.completed_at = datetime.now()
                self._progress.render_dir = pipeline.file_manager.render_dir

                # Get variant paths if any
                variants_dir = pipeline.file_manager.render_dir / "variants"
                if variants_dir.exists():
                    for variant_file in variants_dir.glob("*.mp4"):
                        # Extract ratio from filename like "final_starstitch_16-9.mp4"
                        name_part = variant_file.stem.split("_")[-1]
                        ratio = name_part.replace("-", ":")
                        self._progress.variant_paths[ratio] = variant_file

                self._progress.add_log("Pipeline completed successfully!")

        except Exception as e:
            with self._lock:
                self._progress.status = PipelineStatus.ERROR
                self._progress.error_message = str(e)
                self._progress.completed_at = datetime.now()
                self._progress.add_log(f"ERROR: {e}")

    def _on_progress(self, message: str) -> None:
        """Callback from pipeline for progress updates."""
        with self._lock:
            self._progress.add_log(message)

            # Parse phase markers
            if message.startswith("=== Phase"):
                # Extract phase number and name
                # e.g., "=== Phase 1: Generating Subject Images ==="
                self._progress.current_phase = message.strip("= ").strip()

            # Parse step indicators for image generation
            # e.g., "Generating [1/5]: Celebrity Name"
            img_match = re.search(r"Generating \[(\d+)/(\d+)\]", message)
            if img_match:
                current = int(img_match.group(1))
                self._progress.current_step = current
                self._progress.current_action = message

            # Parse step indicators for morph creation
            # e.g., "Creating morph [1/4]: Person A → Person B"
            morph_match = re.search(r"Creating morph \[(\d+)/(\d+)\]", message)
            if morph_match:
                current = int(morph_match.group(1))
                total_morphs = int(morph_match.group(2))
                # Morphs come after images, so add image count
                num_images = self._progress.total_steps - total_morphs if self._progress.total_steps > 0 else 0
                self._progress.current_step = num_images + current
                self._progress.current_action = message

            # Track overall progress from initial message
            # e.g., "Pipeline started: 5 subjects, 4 morphs"
            if "subjects" in message.lower() and "morphs" in message.lower():
                try:
                    # Parse "Pipeline started: 5 subjects, 4 morphs"
                    subjects_match = re.search(r"(\d+)\s+subjects", message)
                    morphs_match = re.search(r"(\d+)\s+morphs", message)
                    if subjects_match and morphs_match:
                        subjects = int(subjects_match.group(1))
                        morphs = int(morphs_match.group(1))
                        self._progress.total_steps = subjects + morphs
                except (IndexError, ValueError):
                    pass

    def get_progress(self) -> PipelineProgress:
        """Get current progress state (thread-safe copy)."""
        with self._lock:
            # Return a copy to prevent race conditions
            return PipelineProgress(
                status=self._progress.status,
                current_step=self._progress.current_step,
                total_steps=self._progress.total_steps,
                current_phase=self._progress.current_phase,
                current_action=self._progress.current_action,
                logs=self._progress.logs.copy(),
                error_message=self._progress.error_message,
                final_video_path=self._progress.final_video_path,
                variant_paths=self._progress.variant_paths.copy(),
                started_at=self._progress.started_at,
                completed_at=self._progress.completed_at,
                render_dir=self._progress.render_dir,
            )

    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        if self._thread is None:
            return False

        if not self._thread.is_alive():
            # Thread died - check if it was an unexpected termination
            with self._lock:
                if self._progress.status == PipelineStatus.RUNNING:
                    # Thread died unexpectedly
                    self._progress.status = PipelineStatus.ERROR
                    self._progress.error_message = "Pipeline thread terminated unexpectedly"
                    self._progress.completed_at = datetime.now()
            return False

        return True

    def get_status(self) -> PipelineStatus:
        """Get current status."""
        with self._lock:
            return self._progress.status

    def cancel(self) -> None:
        """Request cancellation (best-effort, may not stop mid-API-call)."""
        self._cancel_event.set()
        with self._lock:
            self._progress.status = PipelineStatus.CANCELLED
            self._progress.add_log("Cancellation requested...")

    def reset(self) -> None:
        """Reset the runner for a new run."""
        if self.is_running():
            raise RuntimeError("Cannot reset while running")

        with self._lock:
            self._progress = PipelineProgress()
        self._thread = None
