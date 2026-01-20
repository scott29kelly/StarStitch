"""
Batch Processor
Handles batch processing of multiple config files with queue management.
"""

import json
import logging
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class BatchJobResult:
    """Result of a single batch job."""
    config_path: str
    project_name: str
    status: str  # "success", "failed", "skipped"
    output_path: Optional[str] = None
    duration_seconds: float = 0.0
    estimated_cost: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config_path": self.config_path,
            "project_name": self.project_name,
            "status": self.status,
            "output_path": self.output_path,
            "duration_seconds": self.duration_seconds,
            "estimated_cost": self.estimated_cost,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class BatchSummary:
    """Summary of batch processing results."""
    total_jobs: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_seconds: float = 0.0
    total_estimated_cost: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    interrupted: bool = False
    results: List[BatchJobResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_jobs": self.total_jobs,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_duration_seconds": self.total_duration_seconds,
            "total_estimated_cost": self.total_estimated_cost,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "interrupted": self.interrupted,
            "results": [r.to_dict() for r in self.results]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchSummary":
        """Create from dictionary."""
        summary = cls(
            total_jobs=data.get("total_jobs", 0),
            successful=data.get("successful", 0),
            failed=data.get("failed", 0),
            skipped=data.get("skipped", 0),
            total_duration_seconds=data.get("total_duration_seconds", 0.0),
            total_estimated_cost=data.get("total_estimated_cost", 0.0),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            interrupted=data.get("interrupted", False)
        )
        
        for result_data in data.get("results", []):
            summary.results.append(BatchJobResult(
                config_path=result_data.get("config_path", ""),
                project_name=result_data.get("project_name", ""),
                status=result_data.get("status", "unknown"),
                output_path=result_data.get("output_path"),
                duration_seconds=result_data.get("duration_seconds", 0.0),
                estimated_cost=result_data.get("estimated_cost", 0.0),
                error_message=result_data.get("error_message"),
                started_at=result_data.get("started_at"),
                completed_at=result_data.get("completed_at")
            ))
        
        return summary


class BatchProcessor:
    """
    Manages batch processing of multiple StarStitch configurations.
    
    Features:
    - Process all config.json files in a directory
    - Skip already-completed renders
    - Generate summary report
    - Graceful interruption with resume capability
    - Estimated completion time tracking
    """
    
    # Average times for estimation (can be updated based on history)
    AVG_IMAGE_TIME_SEC = 15.0
    AVG_VIDEO_TIME_SEC = 120.0
    AVG_IMAGE_COST = 0.05
    AVG_VIDEO_COST = 0.50
    
    def __init__(
        self,
        batch_dir: Path,
        on_progress: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the batch processor.
        
        Args:
            batch_dir: Directory containing config files to process.
            on_progress: Optional callback for progress updates.
        """
        self.batch_dir = Path(batch_dir)
        self.on_progress = on_progress or (lambda msg: logger.info(msg))
        
        self.summary = BatchSummary()
        self.manifest_path = self.batch_dir / "batch_manifest.json"
        self.interrupted = False
        self.current_job_index = 0
        
        # Historical averages for better estimates
        self.historical_times: List[float] = []
        
        # Set up signal handlers for graceful interruption
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful interruption."""
        def handle_interrupt(signum, frame):
            self.on_progress("\n⚠️ Interrupt received. Finishing current job and saving progress...")
            self.interrupted = True
        
        signal.signal(signal.SIGINT, handle_interrupt)
        signal.signal(signal.SIGTERM, handle_interrupt)
    
    def discover_configs(self) -> List[Path]:
        """
        Discover all config.json files in the batch directory.
        
        Returns:
            List of paths to config files.
        """
        if not self.batch_dir.exists():
            raise FileNotFoundError(f"Batch directory not found: {self.batch_dir}")
        
        config_files = []
        
        # Look for config.json in the root directory
        root_config = self.batch_dir / "config.json"
        if root_config.exists():
            config_files.append(root_config)
        
        # Look for config.json in subdirectories
        for subdir in self.batch_dir.iterdir():
            if subdir.is_dir():
                config_path = subdir / "config.json"
                if config_path.exists():
                    config_files.append(config_path)
        
        # Also look for any *_config.json files
        for json_file in self.batch_dir.glob("*_config.json"):
            if json_file not in config_files:
                config_files.append(json_file)
        
        # Also look for any .json files that look like configs
        for json_file in self.batch_dir.glob("*.json"):
            if json_file.name not in ["batch_manifest.json", "config.json"]:
                # Quick check if it looks like a StarStitch config
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                    if "sequence" in data and "project_name" in data:
                        if json_file not in config_files:
                            config_files.append(json_file)
                except (json.JSONDecodeError, KeyError):
                    pass
        
        return sorted(config_files)
    
    def is_render_complete(self, config: Dict[str, Any], config_path: Path) -> Optional[Path]:
        """
        Check if a render has already been completed.
        
        Args:
            config: The configuration dictionary.
            config_path: Path to the config file.
            
        Returns:
            Path to the final output if complete, None otherwise.
        """
        output_folder = Path(config.get("output_folder", "renders"))
        project_name = config.get("project_name", "starstitch")
        
        # Check for existing render directories
        if output_folder.exists():
            for render_dir in output_folder.iterdir():
                if render_dir.is_dir() and render_dir.name.startswith("render_"):
                    # Check for final output
                    final_output = render_dir / "final_starstitch.mp4"
                    if final_output.exists():
                        # Verify it matches this config
                        saved_config = render_dir / "config.json"
                        if saved_config.exists():
                            try:
                                with open(saved_config) as f:
                                    saved = json.load(f)
                                if saved.get("project_name") == project_name:
                                    return final_output
                            except (json.JSONDecodeError, KeyError):
                                pass
        
        return None
    
    def estimate_job_time(self, config: Dict[str, Any]) -> tuple:
        """
        Estimate time and cost for a job.
        
        Args:
            config: The configuration dictionary.
            
        Returns:
            Tuple of (estimated_seconds, estimated_cost).
        """
        sequence = config.get("sequence", [])
        num_subjects = len(sequence)
        num_morphs = max(0, num_subjects - 1)
        
        # Use historical average if available
        if self.historical_times:
            avg_job_time = sum(self.historical_times) / len(self.historical_times)
            # Adjust based on number of subjects
            estimated_time = avg_job_time * (num_subjects / 3)  # Assuming 3 subjects as baseline
        else:
            estimated_time = (
                num_subjects * self.AVG_IMAGE_TIME_SEC +
                num_morphs * self.AVG_VIDEO_TIME_SEC
            )
        
        estimated_cost = (
            num_subjects * self.AVG_IMAGE_COST +
            num_morphs * self.AVG_VIDEO_COST
        )
        
        return estimated_time, estimated_cost
    
    def estimate_remaining_time(self) -> float:
        """
        Estimate remaining time for the batch.
        
        Returns:
            Estimated seconds remaining.
        """
        remaining_jobs = self.summary.total_jobs - (
            self.summary.successful + self.summary.failed + self.summary.skipped
        )
        
        if self.historical_times:
            avg_time = sum(self.historical_times) / len(self.historical_times)
        else:
            avg_time = self.AVG_IMAGE_TIME_SEC * 3 + self.AVG_VIDEO_TIME_SEC * 2  # Baseline
        
        return remaining_jobs * avg_time
    
    def format_duration(self, seconds: float) -> str:
        """Format seconds as human-readable duration."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = seconds / 60
            return f"{mins:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def load_manifest(self) -> Optional[BatchSummary]:
        """
        Load existing batch manifest for resume capability.
        
        Returns:
            BatchSummary if manifest exists, None otherwise.
        """
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path) as f:
                    data = json.load(f)
                return BatchSummary.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load manifest: {e}")
        return None
    
    def save_manifest(self):
        """Save the current batch manifest."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self.summary.to_dict(), f, indent=2)
    
    def run(
        self,
        pipeline_factory: Callable[[Dict[str, Any]], Any],
        resume: bool = True
    ) -> BatchSummary:
        """
        Run batch processing.
        
        Args:
            pipeline_factory: Function that creates a pipeline from config dict.
            resume: Whether to resume from previous manifest.
            
        Returns:
            BatchSummary with results.
        """
        self.on_progress(f"\n📦 Batch Processing: {self.batch_dir}")
        self.on_progress("=" * 60)
        
        # Discover configs
        config_files = self.discover_configs()
        
        if not config_files:
            self.on_progress("❌ No config files found in batch directory")
            return self.summary
        
        self.on_progress(f"Found {len(config_files)} config files")
        
        # Load existing manifest for resume
        existing_manifest = None
        if resume:
            existing_manifest = self.load_manifest()
            if existing_manifest and existing_manifest.interrupted:
                self.on_progress(f"📋 Resuming from previous batch (completed: {existing_manifest.successful}/{existing_manifest.total_jobs})")
                self.summary = existing_manifest
                self.summary.interrupted = False
        
        # Initialize summary
        self.summary.total_jobs = len(config_files)
        self.summary.started_at = self.summary.started_at or datetime.now().isoformat()
        
        # Get list of already processed configs
        processed_configs = {r.config_path for r in self.summary.results}
        
        # Process each config
        for i, config_path in enumerate(config_files):
            if self.interrupted:
                self.on_progress(f"\n⏸️ Batch interrupted at job {i + 1}/{len(config_files)}")
                self.summary.interrupted = True
                break
            
            config_path_str = str(config_path)
            
            # Skip if already processed
            if config_path_str in processed_configs:
                self.on_progress(f"\n[{i + 1}/{len(config_files)}] Skipping (already processed): {config_path.name}")
                continue
            
            self.on_progress(f"\n[{i + 1}/{len(config_files)}] Processing: {config_path.name}")
            self.on_progress("-" * 40)
            
            # Load config
            try:
                with open(config_path) as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.on_progress(f"❌ Failed to load config: {e}")
                result = BatchJobResult(
                    config_path=config_path_str,
                    project_name="unknown",
                    status="failed",
                    error_message=str(e)
                )
                self.summary.results.append(result)
                self.summary.failed += 1
                self.save_manifest()
                continue
            
            project_name = config.get("project_name", "unknown")
            
            # Check if already complete
            existing_output = self.is_render_complete(config, config_path)
            if existing_output:
                self.on_progress(f"✓ Already complete: {existing_output}")
                result = BatchJobResult(
                    config_path=config_path_str,
                    project_name=project_name,
                    status="skipped",
                    output_path=str(existing_output)
                )
                self.summary.results.append(result)
                self.summary.skipped += 1
                self.save_manifest()
                continue
            
            # Estimate time/cost
            est_time, est_cost = self.estimate_job_time(config)
            remaining_time = self.estimate_remaining_time()
            
            self.on_progress(f"Project: {project_name}")
            self.on_progress(f"Estimated time: {self.format_duration(est_time)}")
            self.on_progress(f"Remaining batch time: ~{self.format_duration(remaining_time)}")
            
            # Run the pipeline
            start_time = time.time()
            started_at = datetime.now().isoformat()
            
            try:
                pipeline = pipeline_factory(config)
                output_path = pipeline.run()
                
                duration = time.time() - start_time
                self.historical_times.append(duration)
                
                result = BatchJobResult(
                    config_path=config_path_str,
                    project_name=project_name,
                    status="success",
                    output_path=str(output_path),
                    duration_seconds=duration,
                    estimated_cost=est_cost,
                    started_at=started_at,
                    completed_at=datetime.now().isoformat()
                )
                
                self.summary.successful += 1
                self.summary.total_duration_seconds += duration
                self.summary.total_estimated_cost += est_cost
                
                self.on_progress(f"✅ Complete in {self.format_duration(duration)}: {output_path}")
                
            except Exception as e:
                duration = time.time() - start_time
                
                result = BatchJobResult(
                    config_path=config_path_str,
                    project_name=project_name,
                    status="failed",
                    error_message=str(e),
                    duration_seconds=duration,
                    started_at=started_at,
                    completed_at=datetime.now().isoformat()
                )
                
                self.summary.failed += 1
                self.summary.total_duration_seconds += duration
                
                self.on_progress(f"❌ Failed: {e}")
                logger.exception(f"Job failed: {config_path}")
            
            self.summary.results.append(result)
            self.save_manifest()
        
        # Finalize summary
        self.summary.completed_at = datetime.now().isoformat()
        self.save_manifest()
        
        # Print summary
        self._print_summary()
        
        return self.summary
    
    def _print_summary(self):
        """Print the batch summary report."""
        self.on_progress("\n" + "=" * 60)
        self.on_progress("📊 BATCH PROCESSING SUMMARY")
        self.on_progress("=" * 60)
        
        self.on_progress(f"\nTotal jobs:    {self.summary.total_jobs}")
        self.on_progress(f"Successful:    {self.summary.successful} ✅")
        self.on_progress(f"Failed:        {self.summary.failed} ❌")
        self.on_progress(f"Skipped:       {self.summary.skipped} ⏭️")
        
        self.on_progress(f"\nTotal duration: {self.format_duration(self.summary.total_duration_seconds)}")
        self.on_progress(f"Estimated cost: ${self.summary.total_estimated_cost:.2f}")
        
        if self.summary.interrupted:
            self.on_progress("\n⚠️ Batch was interrupted. Run again to resume.")
        
        # List failed jobs
        failed_jobs = [r for r in self.summary.results if r.status == "failed"]
        if failed_jobs:
            self.on_progress("\nFailed jobs:")
            for job in failed_jobs:
                self.on_progress(f"  - {job.project_name}: {job.error_message}")
        
        self.on_progress("\n" + "=" * 60)
        self.on_progress(f"Manifest saved to: {self.manifest_path}")
