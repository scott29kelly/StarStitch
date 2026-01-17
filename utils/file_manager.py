"""
File management utilities for StarStitch.
Handles path construction, folder creation, and asset organization.
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class FileManager:
    """
    Manages file paths and directory structure for render sessions.
    
    Handles creation of timestamped output folders and provides
    consistent path construction for all pipeline assets.
    """

    def __init__(
        self,
        base_output_folder: str = "renders",
        project_name: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the file manager.
        
        Args:
            base_output_folder: Root folder for all render outputs.
            project_name: Optional project name for folder naming.
            logger: Optional logger instance.
        """
        self.base_output_folder = Path(base_output_folder)
        self.project_name = project_name or "starstitch"
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._render_folder: Optional[Path] = None

    @property
    def render_folder(self) -> Path:
        """Get the current render session folder path."""
        if self._render_folder is None:
            raise RuntimeError("Render folder not initialized. Call create_render_folder() first.")
        return self._render_folder

    def create_render_folder(self, timestamp: Optional[str] = None) -> Path:
        """
        Create a timestamped render folder for this session.
        
        Args:
            timestamp: Optional custom timestamp string. If None, current time is used.
            
        Returns:
            Path to the created render folder.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        folder_name = f"render_{timestamp}"
        self._render_folder = self.base_output_folder / folder_name

        self._render_folder.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created render folder: {self._render_folder}")

        return self._render_folder

    def set_render_folder(self, folder_path: Path) -> None:
        """
        Set an existing folder as the render folder (for resume operations).
        
        Args:
            folder_path: Path to the existing render folder.
            
        Raises:
            FileNotFoundError: If the folder doesn't exist.
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Render folder not found: {folder_path}")

        self._render_folder = folder_path
        self.logger.info(f"Using existing render folder: {self._render_folder}")

    def get_anchor_image_path(self, name: str) -> Path:
        """
        Get the path for the anchor (first) image.
        
        Args:
            name: Name identifier for the anchor subject.
            
        Returns:
            Path for the anchor image file.
        """
        safe_name = self._sanitize_name(name)
        return self.render_folder / f"00_anchor_{safe_name}.png"

    def get_target_image_path(self, index: int, name: str) -> Path:
        """
        Get the path for a target image.
        
        Args:
            index: Sequence index (1-based).
            name: Name identifier for the target subject.
            
        Returns:
            Path for the target image file.
        """
        safe_name = self._sanitize_name(name)
        return self.render_folder / f"{index:02d}_target_{safe_name}.png"

    def get_morph_video_path(self, index: int, name: str) -> Path:
        """
        Get the path for a morph video.
        
        Args:
            index: Sequence index (1-based).
            name: Name identifier for the target subject.
            
        Returns:
            Path for the morph video file.
        """
        safe_name = self._sanitize_name(name)
        return self.render_folder / f"{index:02d}_morph_{safe_name}.mp4"

    def get_lastframe_path(self, index: int, name: str) -> Path:
        """
        Get the path for an extracted last frame image.
        
        Args:
            index: Sequence index (1-based).
            name: Name identifier for the target subject.
            
        Returns:
            Path for the last frame image file.
        """
        safe_name = self._sanitize_name(name)
        return self.render_folder / f"{index:02d}_lastframe_{safe_name}.png"

    def get_final_output_path(self) -> Path:
        """
        Get the path for the final concatenated video.
        
        Returns:
            Path for the final output video file.
        """
        return self.render_folder / "final_starstitch.mp4"

    def get_state_file_path(self) -> Path:
        """
        Get the path for the state tracking file.
        
        Returns:
            Path for the state.json file.
        """
        return self.render_folder / "state.json"

    def get_log_file_path(self) -> Path:
        """
        Get the path for the log file.
        
        Returns:
            Path for the starstitch.log file.
        """
        return self.render_folder / "starstitch.log"

    def get_filelist_path(self) -> Path:
        """
        Get the path for the FFMPEG concat filelist.
        
        Returns:
            Path for the filelist.txt file.
        """
        return self.render_folder / "filelist.txt"

    def list_morph_videos(self) -> list[Path]:
        """
        List all morph videos in the render folder, sorted by index.
        
        Returns:
            Sorted list of paths to morph video files.
        """
        videos = list(self.render_folder.glob("*_morph_*.mp4"))
        return sorted(videos)

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use in filenames.
        
        Args:
            name: The name to sanitize.
            
        Returns:
            Sanitized name safe for filesystem use.
        """
        # Replace spaces with underscores, remove special characters
        sanitized = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        return sanitized.lower()

    def ensure_renders_folder_exists(self) -> None:
        """Ensure the base renders folder exists."""
        self.base_output_folder.mkdir(parents=True, exist_ok=True)
