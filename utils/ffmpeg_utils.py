"""
FFMPEG Utilities
Frame extraction and video concatenation using FFMPEG.
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil

logger = logging.getLogger(__name__)


class FFmpegUtils:
    """
    Wrapper for FFMPEG operations.
    
    Handles:
    - Extracting the last frame from a video (for seamless transitions)
    - Concatenating multiple video segments
    - Video format conversions
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize FFMPEG utilities.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable. Defaults to 'ffmpeg' (assumes in PATH).
        """
        self.ffmpeg_path = ffmpeg_path
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> None:
        """Verify that FFMPEG is available."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("FFMPEG returned non-zero exit code")
            
            # Extract version from output
            version_line = result.stdout.split('\n')[0]
            logger.info(f"FFMPEG available: {version_line}")
            
        except FileNotFoundError:
            raise RuntimeError(
                "FFMPEG not found. Please install FFMPEG and ensure it's in your PATH. "
                "See: https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFMPEG version check timed out")
    
    def extract_last_frame(
        self,
        video_path: Path,
        output_path: Path,
        format: str = "png"
    ) -> Path:
        """
        Extract the last frame from a video file.
        
        This is critical for seamless morph chains - the last frame of one
        transition becomes the starting frame of the next.
        
        Args:
            video_path: Path to the input video.
            output_path: Path to save the extracted frame.
            format: Output image format (png recommended for quality).
            
        Returns:
            Path to the extracted frame image.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        logger.info(f"Extracting last frame from: {video_path}")
        
        # Use FFMPEG to get duration and extract last frame
        # -sseof -1 seeks to 1 second before end
        # -update 1 ensures we get the last frame
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output
            "-sseof", "-0.1",  # Seek to 0.1s before end
            "-i", str(video_path),
            "-update", "1",  # Single frame mode
            "-frames:v", "1",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"FFMPEG error: {result.stderr}")
            raise RuntimeError(f"Failed to extract frame: {result.stderr}")
        
        if not output_path.exists():
            raise RuntimeError(f"Frame extraction failed - output file not created")
        
        logger.info(f"Last frame extracted to: {output_path}")
        return output_path
    
    def extract_frame_at_time(
        self,
        video_path: Path,
        output_path: Path,
        time_seconds: float
    ) -> Path:
        """
        Extract a frame at a specific timestamp.
        
        Args:
            video_path: Path to the input video.
            output_path: Path to save the extracted frame.
            time_seconds: Timestamp in seconds.
            
        Returns:
            Path to the extracted frame image.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(time_seconds),
            "-i", str(video_path),
            "-frames:v", "1",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to extract frame: {result.stderr}")
        
        return output_path
    
    def get_video_duration(self, video_path: Path) -> float:
        """
        Get the duration of a video in seconds.
        
        Args:
            video_path: Path to the video file.
            
        Returns:
            Duration in seconds.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get duration: {result.stderr}")
        
        return float(result.stdout.strip())
    
    def concatenate_videos(
        self,
        video_paths: List[Path],
        output_path: Path,
        transition_type: Optional[str] = None
    ) -> Path:
        """
        Concatenate multiple video files into one.
        
        Args:
            video_paths: List of video file paths in order.
            output_path: Path for the final concatenated video.
            transition_type: Optional transition effect (not yet implemented).
            
        Returns:
            Path to the concatenated video.
        """
        if not video_paths:
            raise ValueError("No videos provided for concatenation")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create concat file list
        concat_file = output_path.parent / "concat_list.txt"
        
        with open(concat_file, "w") as f:
            for vp in video_paths:
                # Use absolute paths and escape single quotes
                abs_path = str(Path(vp).absolute()).replace("'", "'\\''")
                f.write(f"file '{abs_path}'\n")
        
        logger.info(f"Concatenating {len(video_paths)} videos...")
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",  # Stream copy for speed
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Clean up concat file
        concat_file.unlink(missing_ok=True)
        
        if result.returncode != 0:
            logger.error(f"Concatenation error: {result.stderr}")
            raise RuntimeError(f"Failed to concatenate videos: {result.stderr}")
        
        logger.info(f"Final video created: {output_path}")
        return output_path
    
    def reencode_for_concat(
        self,
        input_path: Path,
        output_path: Path,
        codec: str = "libx264",
        fps: int = 30
    ) -> Path:
        """
        Re-encode a video to ensure consistent format for concatenation.
        
        Use this if videos have different codecs or settings.
        
        Args:
            input_path: Input video path.
            output_path: Output video path.
            codec: Video codec to use.
            fps: Target frame rate.
            
        Returns:
            Path to the re-encoded video.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-c:v", codec,
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Re-encoding failed: {result.stderr}")
        
        return output_path
    
    def concatenate_with_audio(
        self,
        video_paths: List[Path],
        audio_path: Path,
        output_path: Path,
        audio_settings: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Concatenate videos and merge with an audio track in one operation.
        
        This is more efficient than concatenating first and then adding audio.
        
        Args:
            video_paths: List of video file paths in order.
            audio_path: Path to the processed audio file.
            output_path: Path for the final output video.
            audio_settings: Optional dict with 'volume', 'fade_in_sec', 'fade_out_sec'.
            
        Returns:
            Path to the final video with audio.
        """
        if not video_paths:
            raise ValueError("No videos provided for concatenation")
        
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create concat file list
        concat_file = output_path.parent / "concat_list.txt"
        
        with open(concat_file, "w") as f:
            for vp in video_paths:
                abs_path = str(Path(vp).absolute()).replace("'", "'\\''")
                f.write(f"file '{abs_path}'\n")
        
        logger.info(f"Concatenating {len(video_paths)} videos with audio...")
        
        # Build filter for audio adjustments if needed
        audio_filter = []
        
        if audio_settings:
            volume = audio_settings.get("volume", 1.0)
            if volume != 1.0:
                audio_filter.append(f"volume={volume}")
            
            fade_in = audio_settings.get("fade_in_sec", 0)
            fade_out = audio_settings.get("fade_out_sec", 0)
            
            if fade_in > 0:
                audio_filter.append(f"afade=t=in:st=0:d={fade_in}")
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),  # Video input
            "-i", str(audio_path),    # Audio input
            "-c:v", "copy",           # Copy video stream
            "-c:a", "aac",            # Encode audio as AAC
            "-b:a", "192k",
            "-shortest",              # Match shortest stream
            "-map", "0:v:0",          # Video from concat
            "-map", "1:a:0",          # Audio from audio file
        ]
        
        # Add audio filter if any adjustments needed
        if audio_filter:
            cmd.extend(["-af", ",".join(audio_filter)])
        
        cmd.append(str(output_path))
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Clean up concat file
        concat_file.unlink(missing_ok=True)
        
        if result.returncode != 0:
            logger.error(f"Concatenation with audio error: {result.stderr}")
            raise RuntimeError(f"Failed to concatenate videos with audio: {result.stderr}")
        
        logger.info(f"Final video with audio created: {output_path}")
        return output_path
    
    def add_audio_to_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        replace_existing: bool = True
    ) -> Path:
        """
        Add an audio track to a video file.
        
        Args:
            video_path: Input video file (may or may not have audio).
            audio_path: Audio file to add.
            output_path: Output video file path.
            replace_existing: If True, replace existing audio; if False, mix with it.
            
        Returns:
            Path to the video with audio.
        """
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        
        logger.info(f"Adding audio to video: {video_path.name}")
        
        if replace_existing:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(output_path)
            ]
        else:
            # Mix audio tracks
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=shortest",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path)
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to add audio: {result.stderr}")
        
        logger.info(f"Audio added successfully: {output_path}")
        return output_path
    
    def has_audio_stream(self, video_path: Path) -> bool:
        """
        Check if a video file has an audio stream.
        
        Args:
            video_path: Path to the video file.
            
        Returns:
            True if the video has an audio stream.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        return "audio" in result.stdout.lower()
    
    def get_video_dimensions(self, video_path: Path) -> tuple:
        """
        Get the width and height of a video.
        
        Args:
            video_path: Path to the video file.
            
        Returns:
            Tuple of (width, height).
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get dimensions: {result.stderr}")
        
        parts = result.stdout.strip().split("x")
        return int(parts[0]), int(parts[1])
    
    def parse_aspect_ratio(self, ratio_str: str) -> tuple:
        """
        Parse aspect ratio string to width/height tuple.
        
        Args:
            ratio_str: Aspect ratio string like "16:9" or "9:16".
            
        Returns:
            Tuple of (width_ratio, height_ratio).
        """
        parts = ratio_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid aspect ratio format: {ratio_str}")
        
        return int(parts[0]), int(parts[1])
    
    def calculate_crop_dimensions(
        self,
        src_width: int,
        src_height: int,
        target_ratio: tuple
    ) -> tuple:
        """
        Calculate crop dimensions for a target aspect ratio.
        
        This calculates the largest possible crop area that fits
        the target aspect ratio within the source dimensions.
        
        Args:
            src_width: Source video width.
            src_height: Source video height.
            target_ratio: Target aspect ratio as (w, h).
            
        Returns:
            Tuple of (crop_width, crop_height, x_offset, y_offset).
        """
        target_w, target_h = target_ratio
        target_aspect = target_w / target_h
        src_aspect = src_width / src_height
        
        if target_aspect > src_aspect:
            # Target is wider - crop top/bottom
            crop_width = src_width
            crop_height = int(src_width / target_aspect)
            x_offset = 0
            y_offset = (src_height - crop_height) // 2
        else:
            # Target is taller - crop left/right
            crop_height = src_height
            crop_width = int(src_height * target_aspect)
            x_offset = (src_width - crop_width) // 2
            y_offset = 0
        
        # Ensure even dimensions (required by most codecs)
        crop_width = crop_width - (crop_width % 2)
        crop_height = crop_height - (crop_height % 2)
        
        return crop_width, crop_height, x_offset, y_offset
    
    def create_aspect_ratio_variant(
        self,
        input_path: Path,
        output_path: Path,
        target_ratio: str,
        scale_width: Optional[int] = None
    ) -> Path:
        """
        Create an aspect ratio variant of a video.
        
        This crops the video to the target aspect ratio, centering
        on the middle of the frame.
        
        Args:
            input_path: Path to the input video.
            output_path: Path for the output video.
            target_ratio: Target aspect ratio (e.g., "16:9", "1:1").
            scale_width: Optional width to scale to after cropping.
            
        Returns:
            Path to the output video.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Video not found: {input_path}")
        
        # Get source dimensions
        src_width, src_height = self.get_video_dimensions(input_path)
        target_w, target_h = self.parse_aspect_ratio(target_ratio)
        
        # Calculate crop dimensions
        crop_w, crop_h, x_off, y_off = self.calculate_crop_dimensions(
            src_width, src_height, (target_w, target_h)
        )
        
        logger.info(f"Creating variant: {target_ratio} ({src_width}x{src_height} -> {crop_w}x{crop_h})")
        
        # Build filter chain
        filters = [f"crop={crop_w}:{crop_h}:{x_off}:{y_off}"]
        
        # Add scaling if requested
        if scale_width:
            scale_height = int(scale_width / (target_w / target_h))
            # Ensure even dimensions
            scale_height = scale_height - (scale_height % 2)
            filters.append(f"scale={scale_width}:{scale_height}")
        
        filter_str = ",".join(filters)
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create variant: {result.stderr}")
        
        logger.info(f"Variant created: {output_path}")
        return output_path
    
    def create_all_variants(
        self,
        input_path: Path,
        variants: List[str],
        output_dir: Optional[Path] = None,
        scale_map: Optional[Dict[str, int]] = None
    ) -> Dict[str, Path]:
        """
        Create multiple aspect ratio variants from a single video.
        
        Args:
            input_path: Path to the input video.
            variants: List of aspect ratio strings (e.g., ["16:9", "1:1", "9:16"]).
            output_dir: Directory for output files. Defaults to input directory.
            scale_map: Optional dict mapping ratio to target width.
            
        Returns:
            Dictionary mapping variant names to output paths.
        """
        input_path = Path(input_path)
        
        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        scale_map = scale_map or {}
        
        # Get source aspect ratio to skip if same
        src_width, src_height = self.get_video_dimensions(input_path)
        src_aspect = src_width / src_height
        
        results = {}
        stem = input_path.stem
        suffix = input_path.suffix
        
        for variant in variants:
            target_w, target_h = self.parse_aspect_ratio(variant)
            target_aspect = target_w / target_h
            
            # Skip if aspect ratio matches source (within tolerance)
            if abs(src_aspect - target_aspect) < 0.01:
                logger.info(f"Skipping variant {variant} (matches source)")
                # Just copy the original
                variant_name = variant.replace(":", "x")
                output_path = output_dir / f"{stem}_{variant_name}{suffix}"
                if not output_path.exists():
                    shutil.copy(input_path, output_path)
                results[variant] = output_path
                continue
            
            variant_name = variant.replace(":", "x")
            output_path = output_dir / f"{stem}_{variant_name}{suffix}"
            
            scale_width = scale_map.get(variant)
            
            try:
                self.create_aspect_ratio_variant(
                    input_path,
                    output_path,
                    variant,
                    scale_width
                )
                results[variant] = output_path
            except Exception as e:
                logger.error(f"Failed to create variant {variant}: {e}")
        
        return results
    
    def get_standard_scale_map(self) -> Dict[str, int]:
        """
        Get standard scale widths for common aspect ratios.
        
        Returns:
            Dictionary mapping ratio strings to recommended widths.
        """
        return {
            "9:16": 1080,   # TikTok/Reels (1080x1920)
            "16:9": 1920,   # YouTube landscape (1920x1080)
            "1:1": 1080,    # Instagram square (1080x1080)
            "4:3": 1440,    # Standard (1440x1080)
            "3:4": 1080,    # Portrait standard (1080x1440)
            "4:5": 1080,    # Instagram portrait (1080x1350)
        }
