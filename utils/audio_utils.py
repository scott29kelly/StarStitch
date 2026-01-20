"""
Audio Utilities for StarStitch
FFmpeg-based audio processing for background music tracks.

Features:
- Audio duration detection
- Loop audio to match video length
- Volume adjustment and normalization
- Fade in/out effects
- Audio + video merging
"""

import subprocess
import logging
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioInfo:
    """Information about an audio file."""
    duration: float  # Duration in seconds
    sample_rate: int  # Sample rate in Hz
    channels: int  # Number of audio channels
    codec: str  # Audio codec name
    bitrate: Optional[int] = None  # Bitrate in kbps


class AudioUtils:
    """
    FFmpeg-based audio processing utilities for StarStitch.
    
    Handles:
    - Audio duration and metadata detection
    - Looping audio to match video duration
    - Volume control and normalization
    - Fade in/out effects
    - Merging audio with video
    """
    
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'}
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """
        Initialize audio utilities.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable.
            ffprobe_path: Path to ffprobe executable.
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> None:
        """Verify that FFmpeg is available and has audio support."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg returned non-zero exit code")
            logger.debug("FFmpeg audio utilities initialized")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg with audio support."
            )
    
    def is_supported_format(self, audio_path: Path) -> bool:
        """Check if the audio file format is supported."""
        return Path(audio_path).suffix.lower() in self.SUPPORTED_FORMATS
    
    def get_audio_info(self, audio_path: Path) -> AudioInfo:
        """
        Get detailed information about an audio file.
        
        Args:
            audio_path: Path to the audio file.
            
        Returns:
            AudioInfo with duration, sample rate, channels, etc.
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Use ffprobe to get audio stream info
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=duration,sample_rate,channels,codec_name,bit_rate",
            "-show_entries", "format=duration",
            "-of", "json",
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to probe audio file: {result.stderr}")
        
        import json
        data = json.loads(result.stdout)
        
        # Extract stream info
        stream = data.get("streams", [{}])[0] if data.get("streams") else {}
        format_info = data.get("format", {})
        
        # Duration can be in stream or format
        duration = float(stream.get("duration") or format_info.get("duration", 0))
        
        return AudioInfo(
            duration=duration,
            sample_rate=int(stream.get("sample_rate", 44100)),
            channels=int(stream.get("channels", 2)),
            codec=stream.get("codec_name", "unknown"),
            bitrate=int(stream.get("bit_rate", 0)) // 1000 if stream.get("bit_rate") else None
        )
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file.
            
        Returns:
            Duration in seconds.
        """
        return self.get_audio_info(audio_path).duration
    
    def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_level: float = -16.0
    ) -> Path:
        """
        Normalize audio to a target loudness level.
        
        Uses EBU R128 loudness normalization for consistent volume.
        
        Args:
            input_path: Input audio file.
            output_path: Output normalized audio file.
            target_level: Target integrated loudness in LUFS (default -16).
            
        Returns:
            Path to the normalized audio file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Normalizing audio to {target_level} LUFS...")
        
        # Two-pass loudnorm: first analyze, then normalize
        # Using single-pass with measured=false for simpler implementation
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11",
            "-ar", "48000",  # Standard sample rate
            "-ac", "2",  # Stereo
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Audio normalization failed: {result.stderr}")
        
        logger.info(f"Audio normalized: {output_path}")
        return output_path
    
    def adjust_volume(
        self,
        input_path: Path,
        output_path: Path,
        volume: float = 1.0
    ) -> Path:
        """
        Adjust the volume of an audio file.
        
        Args:
            input_path: Input audio file.
            output_path: Output audio file.
            volume: Volume multiplier (0.0 to 1.0+). 1.0 = original, 0.5 = 50%, 2.0 = 200%.
            
        Returns:
            Path to the volume-adjusted audio file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Adjusting audio volume to {volume * 100:.0f}%...")
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-af", f"volume={volume}",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Volume adjustment failed: {result.stderr}")
        
        return output_path
    
    def apply_fades(
        self,
        input_path: Path,
        output_path: Path,
        fade_in_sec: float = 0.0,
        fade_out_sec: float = 0.0,
        audio_duration: Optional[float] = None
    ) -> Path:
        """
        Apply fade in and/or fade out effects to audio.
        
        Args:
            input_path: Input audio file.
            output_path: Output audio file.
            fade_in_sec: Duration of fade in effect.
            fade_out_sec: Duration of fade out effect.
            audio_duration: Total audio duration (auto-detected if not provided).
            
        Returns:
            Path to the audio file with fades applied.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if fade_in_sec <= 0 and fade_out_sec <= 0:
            # No fades to apply, just copy
            subprocess.run(
                [self.ffmpeg_path, "-y", "-i", str(input_path), "-c", "copy", str(output_path)],
                capture_output=True,
                timeout=60
            )
            return output_path
        
        # Get duration if needed for fade out
        if fade_out_sec > 0 and audio_duration is None:
            audio_duration = self.get_audio_duration(input_path)
        
        # Build filter chain
        filters = []
        
        if fade_in_sec > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in_sec}")
        
        if fade_out_sec > 0 and audio_duration:
            fade_start = max(0, audio_duration - fade_out_sec)
            filters.append(f"afade=t=out:st={fade_start}:d={fade_out_sec}")
        
        filter_str = ",".join(filters)
        
        logger.info(f"Applying audio fades: in={fade_in_sec}s, out={fade_out_sec}s")
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-af", filter_str,
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Fade effect failed: {result.stderr}")
        
        return output_path
    
    def loop_audio_to_duration(
        self,
        input_path: Path,
        output_path: Path,
        target_duration: float
    ) -> Path:
        """
        Loop audio to match a target duration.
        
        If audio is longer than target, it will be trimmed.
        If shorter, it will loop seamlessly.
        
        Args:
            input_path: Input audio file.
            output_path: Output audio file.
            target_duration: Target duration in seconds.
            
        Returns:
            Path to the looped/trimmed audio file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        audio_duration = self.get_audio_duration(input_path)
        
        logger.info(f"Audio duration: {audio_duration:.2f}s, target: {target_duration:.2f}s")
        
        if audio_duration >= target_duration:
            # Audio is longer - just trim
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(input_path),
                "-t", str(target_duration),
                "-c", "copy",
                str(output_path)
            ]
        else:
            # Audio is shorter - loop to match target
            # Calculate how many loops needed
            loops_needed = int(target_duration / audio_duration) + 1
            
            logger.info(f"Looping audio {loops_needed} times to reach target duration")
            
            # Use stream_loop for seamless looping
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-stream_loop", str(loops_needed),
                "-i", str(input_path),
                "-t", str(target_duration),
                "-c:a", "aac",  # Re-encode for proper looping
                "-b:a", "192k",
                str(output_path)
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Audio looping failed: {result.stderr}")
        
        logger.info(f"Audio adjusted to {target_duration:.2f}s: {output_path}")
        return output_path
    
    def trim_audio(
        self,
        input_path: Path,
        output_path: Path,
        duration: float
    ) -> Path:
        """
        Trim audio to a specific duration.
        
        Args:
            input_path: Input audio file.
            output_path: Output audio file.
            duration: Target duration in seconds.
            
        Returns:
            Path to the trimmed audio file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-t", str(duration),
            "-c", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise RuntimeError(f"Audio trimming failed: {result.stderr}")
        
        return output_path
    
    def prepare_audio_for_video(
        self,
        audio_path: Path,
        output_path: Path,
        video_duration: float,
        volume: float = 0.8,
        fade_in_sec: float = 1.0,
        fade_out_sec: float = 2.0,
        loop: bool = True,
        normalize: bool = True
    ) -> Path:
        """
        Prepare audio track for merging with video.
        
        This is the main entry point that chains all audio processing:
        1. Normalize volume (if enabled)
        2. Loop or trim to match video duration
        3. Apply volume adjustment
        4. Apply fade in/out effects
        
        Args:
            audio_path: Input audio file path.
            output_path: Output processed audio file path.
            video_duration: Target video duration in seconds.
            volume: Volume level (0.0 to 1.0).
            fade_in_sec: Fade in duration.
            fade_out_sec: Fade out duration.
            loop: Whether to loop audio if shorter than video.
            normalize: Whether to normalize audio levels.
            
        Returns:
            Path to the fully processed audio file ready for merging.
        """
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Preparing audio track for {video_duration:.2f}s video...")
        
        # Create temp directory for intermediate files
        temp_dir = output_path.parent / "audio_temp"
        temp_dir.mkdir(exist_ok=True)
        
        current_path = audio_path
        step = 0
        
        try:
            # Step 1: Normalize if enabled
            if normalize:
                step += 1
                normalized_path = temp_dir / f"step{step}_normalized.wav"
                current_path = self.normalize_audio(current_path, normalized_path)
            
            # Step 2: Loop or trim to match video duration
            step += 1
            duration_matched_path = temp_dir / f"step{step}_duration.wav"
            
            audio_duration = self.get_audio_duration(current_path)
            
            if loop and audio_duration < video_duration:
                current_path = self.loop_audio_to_duration(
                    current_path, 
                    duration_matched_path, 
                    video_duration
                )
            elif audio_duration > video_duration:
                current_path = self.trim_audio(
                    current_path, 
                    duration_matched_path, 
                    video_duration
                )
            # If audio matches duration exactly, skip this step
            elif audio_duration != video_duration:
                # Close enough, just copy
                current_path = self.trim_audio(
                    current_path,
                    duration_matched_path,
                    video_duration
                )
            
            # Step 3: Apply volume adjustment
            if volume != 1.0:
                step += 1
                volume_path = temp_dir / f"step{step}_volume.wav"
                current_path = self.adjust_volume(current_path, volume_path, volume)
            
            # Step 4: Apply fades (this outputs to final location)
            if fade_in_sec > 0 or fade_out_sec > 0:
                current_path = self.apply_fades(
                    current_path,
                    output_path,
                    fade_in_sec=fade_in_sec,
                    fade_out_sec=fade_out_sec,
                    audio_duration=video_duration
                )
            else:
                # No fades, just copy to output
                subprocess.run(
                    [self.ffmpeg_path, "-y", "-i", str(current_path), "-c", "copy", str(output_path)],
                    capture_output=True,
                    timeout=60
                )
                current_path = output_path
            
            logger.info(f"Audio preparation complete: {output_path}")
            return output_path
            
        finally:
            # Clean up temp files
            if temp_dir.exists():
                for temp_file in temp_dir.glob("step*"):
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                try:
                    temp_dir.rmdir()
                except Exception:
                    pass
    
    def merge_audio_with_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        video_has_audio: bool = False
    ) -> Path:
        """
        Merge an audio track with a video file.
        
        Args:
            video_path: Input video file.
            audio_path: Processed audio file (should match video duration).
            output_path: Output video file with audio.
            video_has_audio: If True, replace existing audio; if False, add audio track.
            
        Returns:
            Path to the video file with merged audio.
        """
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Merging audio with video: {output_path}")
        
        if video_has_audio:
            # Replace existing audio
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy",  # Copy video stream without re-encoding
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",  # Take video from first input
                "-map", "1:a:0",  # Take audio from second input
                "-shortest",
                str(output_path)
            ]
        else:
            # Add audio to silent video
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_path)
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise RuntimeError(f"Audio-video merge failed: {result.stderr}")
        
        logger.info(f"Audio merged successfully: {output_path}")
        return output_path
