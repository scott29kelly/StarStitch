"""
Video generation provider using Fal.ai API.
Implements the Kling v1.6 Pro model for image-to-video morphing.
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any

import fal_client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_provider import BaseProvider, VideoGenerationError


class VideoGenerator(BaseProvider):
    """
    Video generation provider using Fal.ai's Kling v1.6 Pro model.
    
    Generates smooth morphing transitions between two images.
    """

    DEFAULT_MODEL = "fal-ai/kling-video/v1.6/pro/image-to-video"
    VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16"]
    VALID_DURATIONS = ["5", "10"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Fal.ai video generator.
        
        Args:
            api_key: Fal.ai API key. If None, reads from FAL_KEY env var.
            model: Model identifier. Defaults to Kling v1.6 Pro.
            logger: Optional logger instance.
        """
        self._api_key = api_key or os.environ.get("FAL_KEY", "")
        self._model = model or self.DEFAULT_MODEL
        super().__init__(self._api_key, logger)

    def _validate_credentials(self) -> None:
        """Validate Fal.ai API credentials."""
        if not self._api_key:
            raise VideoGenerationError(
                "Fal.ai API key not configured. Set FAL_KEY environment variable.",
                provider=self.provider_name,
            )
        # Set the key for the fal_client library
        os.environ["FAL_KEY"] = self._api_key

    @property
    def provider_name(self) -> str:
        return "Fal.ai"

    @property
    def model_name(self) -> str:
        return self._model

    def upload_image(self, image_path: Path) -> str:
        """
        Upload a local image to Fal.ai storage to get a public URL.
        
        Args:
            image_path: Path to the local image file.
            
        Returns:
            Public URL of the uploaded image.
            
        Raises:
            VideoGenerationError: If upload fails.
        """
        self.logger.debug(f"Uploading image: {image_path}")

        try:
            url = fal_client.upload_file(str(image_path))
            self.logger.debug(f"Image uploaded successfully: {url}")
            return url
        except Exception as e:
            raise VideoGenerationError(
                f"Failed to upload image to Fal.ai: {str(e)}",
                provider=self.provider_name,
                details={"image_path": str(image_path), "error": str(e)},
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        retry=retry_if_exception_type((requests.RequestException, Exception)),
        reraise=True,
    )
    def generate(
        self,
        start_image_path: Path,
        end_image_path: Path,
        output_path: Path,
        prompt: str = "smooth morphing transition between two people",
        duration: str = "5",
        aspect_ratio: str = "9:16",
    ) -> Path:
        """
        Generate a morphing video between two images using Fal.ai's Kling model.
        
        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            output_path: Path where the generated video should be saved.
            prompt: Transition description prompt.
            duration: Video duration in seconds ("5" or "10").
            aspect_ratio: Aspect ratio of the output video.
            
        Returns:
            Path to the saved video file.
            
        Raises:
            VideoGenerationError: If generation fails after retries.
        """
        # Validate parameters
        if duration not in self.VALID_DURATIONS:
            self.logger.warning(f"Invalid duration '{duration}', defaulting to '5'")
            duration = "5"

        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            self.logger.warning(f"Invalid aspect ratio '{aspect_ratio}', defaulting to '9:16'")
            aspect_ratio = "9:16"

        # Verify input files exist
        if not start_image_path.exists():
            raise VideoGenerationError(
                f"Start image not found: {start_image_path}",
                provider=self.provider_name,
            )
        if not end_image_path.exists():
            raise VideoGenerationError(
                f"End image not found: {end_image_path}",
                provider=self.provider_name,
            )

        self.log_api_call(
            "Generating morph video",
            {
                "start_image": str(start_image_path.name),
                "end_image": str(end_image_path.name),
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            },
        )

        start_time = time.time()

        try:
            # Upload both images to get public URLs
            self.logger.info("Uploading start image to Fal.ai storage...")
            start_image_url = self.upload_image(start_image_path)

            self.logger.info("Uploading end image to Fal.ai storage...")
            end_image_url = self.upload_image(end_image_path)

            # Build API arguments
            arguments: Dict[str, Any] = {
                "prompt": prompt,
                "image_url": start_image_url,
                "end_image_url": end_image_url,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }

            self.logger.info(f"Submitting video generation request (duration={duration}s)...")

            # Call the Fal.ai API with subscription (polls until complete)
            def on_queue_update(update):
                if isinstance(update, fal_client.InProgress):
                    for log in update.logs:
                        self.logger.debug(f"[Fal.ai Log] {log['message']}")

            result = fal_client.subscribe(
                self._model,
                arguments=arguments,
                with_logs=True,
                on_queue_update=on_queue_update,
            )

            # Extract video URL from result
            video_url = self._extract_video_url(result)

            # Download the video
            self._download_video(video_url, output_path)

            duration_elapsed = time.time() - start_time
            self.log_api_response("Video generation", success=True, duration=duration_elapsed)

            self.logger.info(f"Video saved to: {output_path}")
            return output_path

        except Exception as e:
            duration_elapsed = time.time() - start_time
            self.log_api_response("Video generation", success=False, duration=duration_elapsed)
            raise VideoGenerationError(
                f"Video generation failed: {str(e)}",
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e

    def _extract_video_url(self, result: Dict[str, Any]) -> str:
        """
        Extract the video URL from the Fal.ai response.
        
        Args:
            result: The API response dictionary.
            
        Returns:
            URL of the generated video.
            
        Raises:
            VideoGenerationError: If URL cannot be extracted.
        """
        # Try common response structures
        if isinstance(result, dict):
            # Check for 'video' key with 'url' subkey
            if "video" in result and isinstance(result["video"], dict):
                if "url" in result["video"]:
                    return result["video"]["url"]
            
            # Check for direct 'video_url' key
            if "video_url" in result:
                return result["video_url"]
            
            # Check for 'url' key directly
            if "url" in result:
                return result["url"]
            
            # Check for 'output' key
            if "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    return output
                if isinstance(output, dict) and "url" in output:
                    return output["url"]

        raise VideoGenerationError(
            f"Could not extract video URL from response: {result}",
            provider=self.provider_name,
            details={"response": str(result)[:500]},
        )

    def _download_video(self, url: str, output_path: Path) -> None:
        """
        Download a video from a URL and save it locally.
        
        Args:
            url: The URL of the video to download.
            output_path: Path where the video should be saved.
            
        Raises:
            VideoGenerationError: If download fails.
        """
        try:
            self.logger.info(f"Downloading video from Fal.ai...")
            response = requests.get(url, timeout=300, stream=True)
            response.raise_for_status()

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Stream download for large files
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.debug(f"Video downloaded: {output_path}")

        except requests.RequestException as e:
            raise VideoGenerationError(
                f"Failed to download video from {url}: {str(e)}",
                provider=self.provider_name,
                details={"url": url, "error": str(e)},
            ) from e
