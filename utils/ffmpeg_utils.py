"""
FFMPEG utilities for StarStitch.
Handles frame extraction and video concatenation.
"""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, List


class FFmpegError(Exception):
    """Exception for FFMPEG-related errors."""

    def __init__(self, message: str, command: Optional[str] = None, stderr: Optional[str] = None):
        super().__init__(message)
        self.command = command
        self.stderr = stderr


class FFmpegUtils:
    """
    FFMPEG utility class for video processing operations.
    
    Provides methods for extracting frames and concatenating videos.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize FFMPEG utilities.
        
        Args:
            logger: Optional logger instance.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._ffmpeg_path: Optional[str] = None

    @property
    def ffmpeg_path(self) -> str:
        """Get the path to the FFMPEG executable."""
        if self._ffmpeg_path is None:
            self._ffmpeg_path = self._find_ffmpeg()
        return self._ffmpeg_path

    def _find_ffmpeg(self) -> str:
        """
        Find the FFMPEG executable in the system PATH.
        
        Returns:
            Path to the FFMPEG executable.
            
        Raises:
            FFmpegError: If FFMPEG is not found.
        """
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            raise FFmpegError(
                "FFMPEG not found in system PATH. Please install FFMPEG and ensure it's accessible."
            )
        self.logger.debug(f"Found FFMPEG at: {ffmpeg_path}")
        return ffmpeg_path

    def check_availability(self) -> bool:
        """
        Check if FFMPEG is available and working.
        
        Returns:
            True if FFMPEG is available, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Extract version info from first line
                version_line = result.stdout.split("\n")[0]
                self.logger.info(f"FFMPEG available: {version_line}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError, FFmpegError):
            return False

    def extract_last_frame(self, video_path: Path, output_path: Path) -> Path:
        """
        Extract the last frame from a video.
        
        Uses FFMPEG's -sseof flag to seek to 1 second before the end,
        then extracts a single frame with high quality.
        
        Args:
            video_path: Path to the input video file.
            output_path: Path where the extracted frame should be saved.
            
        Returns:
            Path to the extracted frame image.
            
        Raises:
            FFmpegError: If frame extraction fails.
        """
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Extracting last frame from: {video_path.name}")

        # Command: ffmpeg -sseof -1 -i input.mp4 -update 1 -q:v 1 output.png
        # -sseof -1: Seek to 1 second before end of file
        # -update 1: Only keep the last frame (overwrite mode)
        # -q:v 1: Highest quality for output image
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output file if exists
            "-sseof", "-0.1",  # Seek to 0.1 seconds before end (more precise for last frame)
            "-i", str(video_path),
            "-update", "1",
            "-q:v", "1",
            "-frames:v", "1",  # Only extract 1 frame
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise FFmpegError(
                    f"FFMPEG frame extraction failed with code {result.returncode}",
                    command=" ".join(cmd),
                    stderr=result.stderr,
                )

            if not output_path.exists():
                raise FFmpegError(
                    f"FFMPEG completed but output file not found: {output_path}",
                    command=" ".join(cmd),
                )

            self.logger.info(f"Last frame extracted: {output_path.name}")
            return output_path

        except subprocess.TimeoutExpired:
            raise FFmpegError(
                "FFMPEG frame extraction timed out after 60 seconds",
                command=" ".join(cmd),
            )

    def concatenate_videos(
        self,
        video_paths: List[Path],
        output_path: Path,
        filelist_path: Optional[Path] = None,
    ) -> Path:
        """
        Concatenate multiple videos into a single output file.
        
        Uses FFMPEG's concat demuxer for lossless concatenation
        when videos have compatible codecs.
        
        Args:
            video_paths: List of paths to video files to concatenate.
            output_path: Path where the concatenated video should be saved.
            filelist_path: Optional path for the intermediate filelist.txt.
                          If None, creates one next to output_path.
                          
        Returns:
            Path to the concatenated video file.
            
        Raises:
            FFmpegError: If concatenation fails.
        """
        if not video_paths:
            raise FFmpegError("No video files provided for concatenation")

        # Verify all input files exist
        for video_path in video_paths:
            if not video_path.exists():
                raise FFmpegError(f"Video file not found: {video_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create filelist for concat demuxer
        if filelist_path is None:
            filelist_path = output_path.parent / "filelist.txt"

        self._create_filelist(video_paths, filelist_path)

        self.logger.info(f"Concatenating {len(video_paths)} videos...")

        # Command: ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output file if exists
            "-f", "concat",
            "-safe", "0",
            "-i", str(filelist_path),
            "-c", "copy",  # Copy streams without re-encoding
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout for longer videos
            )

            if result.returncode != 0:
                raise FFmpegError(
                    f"FFMPEG concatenation failed with code {result.returncode}",
                    command=" ".join(cmd),
                    stderr=result.stderr,
                )

            if not output_path.exists():
                raise FFmpegError(
                    f"FFMPEG completed but output file not found: {output_path}",
                    command=" ".join(cmd),
                )

            # Get output file size
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"Concatenated video created: {output_path.name} ({file_size_mb:.1f} MB)")

            return output_path

        except subprocess.TimeoutExpired:
            raise FFmpegError(
                "FFMPEG concatenation timed out after 5 minutes",
                command=" ".join(cmd),
            )

    def _create_filelist(self, video_paths: List[Path], filelist_path: Path) -> None:
        """
        Create a filelist.txt for FFMPEG concat demuxer.
        
        Args:
            video_paths: List of video file paths.
            filelist_path: Path where filelist.txt should be written.
        """
        with open(filelist_path, "w") as f:
            for video_path in video_paths:
                # Use absolute paths and escape single quotes
                abs_path = video_path.resolve()
                escaped_path = str(abs_path).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        self.logger.debug(f"Created filelist: {filelist_path}")

    def get_video_duration(self, video_path: Path) -> float:
        """
        Get the duration of a video in seconds.
        
        Args:
            video_path: Path to the video file.
            
        Returns:
            Duration in seconds.
            
        Raises:
            FFmpegError: If duration cannot be determined.
        """
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")

        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path is None:
            raise FFmpegError("ffprobe not found in system PATH")

        cmd = [
            ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise FFmpegError(
                    f"ffprobe failed with code {result.returncode}",
                    command=" ".join(cmd),
                    stderr=result.stderr,
                )

            duration = float(result.stdout.strip())
            return duration

        except (ValueError, subprocess.TimeoutExpired) as e:
            raise FFmpegError(
                f"Could not determine video duration: {e}",
                command=" ".join(cmd),
            )
