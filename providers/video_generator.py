"""
Video Generator - Fal.ai API Wrapper
Generates morphing transition videos using Kling and other models via Fal.ai.
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Callable

try:
    import fal_client
except ImportError:
    fal_client = None

logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    Generates morphing videos using Fal.ai's API.
    
    Supports multiple models:
    - fal-ai/kling-video/v1.6/pro/image-to-video (default, best quality)
    - fal-ai/kling-video/v1.5/pro/image-to-video
    - fal-ai/luma-dream-machine
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "fal-ai/kling-video/v1.6/pro/image-to-video"
    ):
        """
        Initialize the video generator.
        
        Args:
            api_key: Fal.ai API key. If None, reads from FAL_KEY env.
            model: The model identifier to use for generation.
        """
        self.api_key = api_key or os.environ.get("FAL_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "Fal.ai API key required. Set FAL_KEY environment variable "
                "or pass api_key to constructor."
            )
        
        if fal_client is None:
            raise ImportError("fal-client package not installed. Run: pip install fal-client")
        
        # Set key for fal client
        os.environ["FAL_KEY"] = self.api_key
        
        logger.info(f"VideoGenerator initialized with model: {self.model}")
    
    def generate(
        self,
        start_image_url: str,
        end_image_url: Optional[str] = None,
        prompt: str = "",
        duration_seconds: int = 5,
        aspect_ratio: str = "9:16",
        output_path: Optional[Path] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Generate a morphing video between two images.
        
        Args:
            start_image_url: URL of the starting image.
            end_image_url: URL of the ending image (for morph transitions).
            prompt: Optional motion/action prompt.
            duration_seconds: Duration of the video in seconds.
            aspect_ratio: The aspect ratio.
            output_path: Optional path to save the video.
            on_progress: Optional callback for progress updates.
            
        Returns:
            The URL of the generated video, or local path if output_path is provided.
        """
        if on_progress:
            on_progress(f"Generating {duration_seconds}s video with {self.model}...")
        
        logger.info(f"Generating video: {start_image_url[:50]}... -> {end_image_url[:50] if end_image_url else 'motion'}...")
        
        # Build input parameters based on model
        input_params = {
            "prompt": prompt or "smooth, natural transition, subtle movement",
            "image_url": start_image_url,
            "duration": str(duration_seconds),
            "aspect_ratio": aspect_ratio,
        }
        
        # Add end image for morph-style models
        if end_image_url:
            input_params["tail_image_url"] = end_image_url
        
        try:
            # Submit the job
            if on_progress:
                on_progress("Submitting to Fal.ai queue...")
            
            handler = fal_client.submit(self.model, arguments=input_params)
            
            # Poll for completion
            result = self._poll_for_result(handler, on_progress)
            
            # Extract video URL from result
            video_url = self._extract_video_url(result)
            
            if not video_url:
                raise RuntimeError("No video URL returned from Fal.ai")
            
            logger.info(f"Video generated: {video_url}")
            
            # Download if output path specified
            if output_path:
                if on_progress:
                    on_progress(f"Downloading to {output_path}...")
                
                self._download_video(video_url, output_path)
                return str(output_path)
            
            return video_url
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise
    
    def _poll_for_result(
        self,
        handler,
        on_progress: Optional[Callable[[str], None]] = None,
        poll_interval: int = 5,
        max_wait: int = 600
    ) -> Dict[str, Any]:
        """Poll Fal.ai for job completion."""
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait:
                raise TimeoutError(f"Video generation timed out after {max_wait}s")
            
            status = handler.status()
            
            if hasattr(status, "completed") and status.completed:
                return handler.get()
            
            if hasattr(status, "status"):
                status_str = status.status
                if on_progress:
                    on_progress(f"Status: {status_str} ({int(elapsed)}s elapsed)")
                
                if status_str == "COMPLETED":
                    return handler.get()
                elif status_str == "FAILED":
                    raise RuntimeError("Video generation failed on Fal.ai")
            
            time.sleep(poll_interval)
    
    def _extract_video_url(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract video URL from Fal.ai result."""
        # Handle different result structures
        if isinstance(result, dict):
            # Check common keys
            if "video" in result:
                video = result["video"]
                if isinstance(video, dict) and "url" in video:
                    return video["url"]
                elif isinstance(video, str):
                    return video
            
            if "video_url" in result:
                return result["video_url"]
            
            if "url" in result:
                return result["url"]
            
            # Nested output
            if "output" in result:
                return self._extract_video_url(result["output"])
        
        return None
    
    def _download_video(self, url: str, output_path: Path) -> None:
        """Download a video from URL to local path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Video saved to: {output_path}")
    
    def create_morph(
        self,
        start_image_path: Path,
        end_image_path: Path,
        duration_seconds: int = 5,
        aspect_ratio: str = "9:16",
        output_path: Optional[Path] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Create a morph transition between two local images.
        
        This is a convenience method that handles uploading local files.
        
        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            duration_seconds: Duration of the morph video.
            aspect_ratio: The aspect ratio.
            output_path: Optional path to save the video.
            on_progress: Optional progress callback.
            
        Returns:
            URL or file path of the generated video.
        """
        # Upload images to Fal's file storage
        if on_progress:
            on_progress("Uploading images to Fal.ai...")
        
        start_url = fal_client.upload_file(str(start_image_path))
        end_url = fal_client.upload_file(str(end_image_path))
        
        return self.generate(
            start_image_url=start_url,
            end_image_url=end_url,
            prompt="smooth morphing transition, natural movement",
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            output_path=output_path,
            on_progress=on_progress
        )
