"""
File Manager
Handles asset organization, naming conventions, and resume logic.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file organization and resume capability for StarStitch renders.
    
    Directory structure:
        renders/
        └── render_{timestamp}/
            ├── manifest.json      # Resume state
            ├── config.json        # Original config
            ├── 00_anchor.png      # Starting image
            ├── 01_target.png      # First morph target
            ├── 01_morph.mp4       # First morph video
            ├── 01_lastframe.png   # Extracted for next morph
            ├── 02_target.png
            ├── 02_morph.mp4
            ├── 02_lastframe.png
            ├── ...
            └── final_starstitch.mp4
    """
    
    def __init__(self, base_output_dir: str = "renders", project_name: str = "starstitch"):
        """
        Initialize the file manager.
        
        Args:
            base_output_dir: Base directory for all renders.
            project_name: Name of the current project.
        """
        self.base_output_dir = Path(base_output_dir)
        self.project_name = project_name
        self.render_dir: Optional[Path] = None
        self.manifest: Dict[str, Any] = {}
    
    def create_render_session(self) -> Path:
        """
        Create a new render session directory.
        
        Returns:
            Path to the new render directory.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.render_dir = self.base_output_dir / f"render_{timestamp}"
        self.render_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize manifest
        self.manifest = {
            "project_name": self.project_name,
            "created_at": datetime.now().isoformat(),
            "status": "initialized",
            "current_step": 0,
            "total_steps": 0,
            "completed_steps": [],
            "assets": {
                "images": {},
                "videos": {},
                "frames": {}
            },
            "errors": []
        }
        
        self._save_manifest()
        
        logger.info(f"Created render session: {self.render_dir}")
        return self.render_dir
    
    def load_session(self, render_dir: Path) -> Dict[str, Any]:
        """
        Load an existing render session for resume.
        
        Args:
            render_dir: Path to the render directory to resume.
            
        Returns:
            The loaded manifest.
        """
        self.render_dir = Path(render_dir)
        manifest_path = self.render_dir / "manifest.json"
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest found in {render_dir}")
        
        with open(manifest_path, "r") as f:
            self.manifest = json.load(f)
        
        logger.info(f"Loaded session from {render_dir}, step {self.manifest.get('current_step', 0)}")
        return self.manifest
    
    def _save_manifest(self) -> None:
        """Save the current manifest to disk."""
        if not self.render_dir:
            raise RuntimeError("No render session active")
        
        manifest_path = self.render_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)
    
    def save_config(self, config: Dict[str, Any]) -> Path:
        """
        Save the original config to the render directory.
        
        Args:
            config: The configuration dictionary.
            
        Returns:
            Path to the saved config file.
        """
        if not self.render_dir:
            raise RuntimeError("No render session active")
        
        config_path = self.render_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    def get_image_path(self, step: int, image_type: str) -> Path:
        """
        Get the path for an image file.
        
        Args:
            step: The step number (0 for anchor).
            image_type: One of "anchor", "target", "lastframe".
            
        Returns:
            Path for the image file.
        """
        if not self.render_dir:
            raise RuntimeError("No render session active")
        
        if image_type == "anchor":
            return self.render_dir / "00_anchor.png"
        elif image_type == "target":
            return self.render_dir / f"{step:02d}_target.png"
        elif image_type == "lastframe":
            return self.render_dir / f"{step:02d}_lastframe.png"
        else:
            raise ValueError(f"Unknown image type: {image_type}")
    
    def get_video_path(self, step: int) -> Path:
        """
        Get the path for a morph video file.
        
        Args:
            step: The step number.
            
        Returns:
            Path for the video file.
        """
        if not self.render_dir:
            raise RuntimeError("No render session active")
        
        return self.render_dir / f"{step:02d}_morph.mp4"
    
    def get_final_output_path(self) -> Path:
        """Get the path for the final concatenated video."""
        if not self.render_dir:
            raise RuntimeError("No render session active")
        
        return self.render_dir / "final_starstitch.mp4"
    
    def mark_step_complete(
        self,
        step: int,
        step_type: str,
        asset_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark a step as complete and record the asset.
        
        Args:
            step: The step number.
            step_type: One of "image", "video", "frame".
            asset_path: Path to the generated asset.
            metadata: Optional additional metadata.
        """
        step_key = f"{step}_{step_type}"
        
        self.manifest["completed_steps"].append(step_key)
        self.manifest["current_step"] = step
        
        # Record asset
        category = {
            "image": "images",
            "video": "videos",
            "frame": "frames"
        }.get(step_type, "images")
        
        self.manifest["assets"][category][step_key] = {
            "path": str(asset_path),
            "completed_at": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        self._save_manifest()
        logger.info(f"Step {step_key} completed: {asset_path}")
    
    def is_step_complete(self, step: int, step_type: str) -> bool:
        """
        Check if a step has already been completed.
        
        Args:
            step: The step number.
            step_type: The type of step.
            
        Returns:
            True if the step is complete and the asset exists.
        """
        step_key = f"{step}_{step_type}"
        
        if step_key not in self.manifest.get("completed_steps", []):
            return False
        
        # Verify the file actually exists
        category = {
            "image": "images",
            "video": "videos",
            "frame": "frames"
        }.get(step_type, "images")
        
        asset_info = self.manifest["assets"].get(category, {}).get(step_key, {})
        asset_path = asset_info.get("path")
        
        if asset_path and Path(asset_path).exists():
            return True
        
        return False
    
    def set_status(self, status: str, error: Optional[str] = None) -> None:
        """
        Update the render status.
        
        Args:
            status: One of "initialized", "running", "paused", "complete", "error".
            error: Optional error message if status is "error".
        """
        self.manifest["status"] = status
        self.manifest["updated_at"] = datetime.now().isoformat()
        
        if error:
            self.manifest["errors"].append({
                "time": datetime.now().isoformat(),
                "message": error
            })
        
        self._save_manifest()
    
    def set_total_steps(self, total: int) -> None:
        """Set the total number of steps for progress tracking."""
        self.manifest["total_steps"] = total
        self._save_manifest()
    
    def get_all_video_paths(self) -> List[Path]:
        """
        Get all morph video paths in order for concatenation.
        
        Returns:
            List of video paths in sequence order.
        """
        if not self.render_dir:
            return []
        
        videos = []
        step = 1
        
        while True:
            video_path = self.get_video_path(step)
            if video_path.exists():
                videos.append(video_path)
                step += 1
            else:
                break
        
        return videos
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary files after successful render."""
        if not self.render_dir:
            return
        
        # Remove concat list if it exists
        concat_list = self.render_dir / "concat_list.txt"
        if concat_list.exists():
            concat_list.unlink()
        
        logger.info("Temporary files cleaned up")
