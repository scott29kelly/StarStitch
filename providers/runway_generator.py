"""
Video generation provider using Runway ML API.
Implements the Gen-3 Alpha Turbo model for image-to-video morphing.
"""

import os
import time
import logging
import requests
import base64
from pathlib import Path
from typing import Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_video_generator import BaseVideoGenerator
from .base_provider import VideoGenerationError


class RunwayVideoGenerator(BaseVideoGenerator):
    """
    Video generation provider using Runway ML's Gen-3 Alpha Turbo model.
    
    Generates smooth morphing transitions between two images using
    Runway's Gen-3 Alpha Turbo model, which excels at high-quality,
    fast video generation with consistent motion.
    
    API Documentation: https://docs.runwayml.com/
    """

    PROVIDER_ID = "runway"
    DEFAULT_MODEL = "gen3a_turbo"
    VALID_ASPECT_RATIOS = ["16:9", "9:16"]  # Runway supports these
    VALID_DURATIONS = ["5", "10"]  # Maps to Runway's duration options
    ENV_KEY_NAME = "RUNWAY_API_KEY"
    
    API_BASE_URL = "https://api.runwayml.com/v1"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_name(self) -> str:
        return "Runway ML"

    def _get_default_api_key(self) -> str:
        return os.environ.get(self.ENV_KEY_NAME, "")

    def _validate_credentials(self) -> None:
        """Validate Runway ML API credentials."""
        if not self._api_key:
            raise VideoGenerationError(
                f"Runway ML API key not configured. Set {self.ENV_KEY_NAME} environment variable.",
                provider=self.provider_name,
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Runway API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

    def _encode_image_to_base64(self, image_path: Path) -> str:
        """
        Encode an image file to base64 data URI.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Base64 encoded data URI string.
        """
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Determine MIME type from extension
        extension = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(extension, "image/png")
        
        encoded = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _duration_to_seconds(self, duration: str) -> int:
        """Convert duration string to integer seconds for Runway API."""
        return int(duration)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        retry=retry_if_exception_type((requests.RequestException,)),
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
        Generate a morphing video between two images using Runway's Gen-3 Alpha Turbo.
        
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
        # Validate inputs
        duration, aspect_ratio = self.validate_inputs(
            start_image_path, end_image_path, duration, aspect_ratio
        )

        self.log_api_call(
            "Generating morph video",
            {
                "start_image": str(start_image_path.name),
                "end_image": str(end_image_path.name),
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "model": self._model,
            },
        )

        start_time = time.time()

        try:
            # Encode images to base64
            self.logger.info("Encoding start image for Runway...")
            start_image_data = self._encode_image_to_base64(start_image_path)

            self.logger.info("Encoding end image for Runway...")
            end_image_data = self._encode_image_to_base64(end_image_path)

            # Create the generation task
            task_id = self._create_generation_task(
                start_image_data=start_image_data,
                end_image_data=end_image_data,
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
            )

            self.logger.info(f"Task created: {task_id}, polling for completion...")

            # Poll for completion
            video_url = self._poll_for_completion(task_id)

            # Download the video
            self.download_video(video_url, output_path)

            duration_elapsed = time.time() - start_time
            self.log_api_response("Video generation", success=True, duration=duration_elapsed)

            self.logger.info(f"Video saved to: {output_path}")
            return output_path

        except VideoGenerationError:
            raise
        except Exception as e:
            duration_elapsed = time.time() - start_time
            self.log_api_response("Video generation", success=False, duration=duration_elapsed)
            raise VideoGenerationError(
                f"Video generation failed: {str(e)}",
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e

    def _create_generation_task(
        self,
        start_image_data: str,
        end_image_data: str,
        prompt: str,
        duration: str,
        aspect_ratio: str,
    ) -> str:
        """
        Create a video generation task on Runway.
        
        Args:
            start_image_data: Base64 encoded start image.
            end_image_data: Base64 encoded end image.
            prompt: Text prompt for the transition.
            duration: Video duration in seconds.
            aspect_ratio: Aspect ratio string.
            
        Returns:
            Task ID for polling.
            
        Raises:
            VideoGenerationError: If task creation fails.
        """
        url = f"{self.API_BASE_URL}/image_to_video"
        
        # Build the request payload
        # Runway Gen-3 uses promptImage for start and can use lastFrame for end
        payload = {
            "model": self._model,
            "promptImage": start_image_data,
            "promptText": prompt,
            "duration": self._duration_to_seconds(duration),
            "ratio": aspect_ratio,
        }
        
        # Add end frame if provided (for morphing effect)
        # Runway supports first/last frame keyframing
        if end_image_data:
            payload["lastFrame"] = end_image_data

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            
            result = response.json()
            task_id = result.get("id")
            
            if not task_id:
                raise VideoGenerationError(
                    f"No task ID in Runway response: {result}",
                    provider=self.provider_name,
                    details={"response": str(result)[:500]},
                )
            
            return task_id
            
        except requests.RequestException as e:
            error_detail = ""
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text[:500]
            
            raise VideoGenerationError(
                f"Failed to create Runway task: {str(e)}",
                provider=self.provider_name,
                details={"error": str(e), "response": error_detail},
            ) from e

    def _poll_for_completion(
        self,
        task_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 5,
    ) -> str:
        """
        Poll the Runway API until the task completes.
        
        Args:
            task_id: The task ID to poll.
            max_wait_time: Maximum time to wait in seconds.
            poll_interval: Time between polls in seconds.
            
        Returns:
            URL of the generated video.
            
        Raises:
            VideoGenerationError: If task fails or times out.
        """
        url = f"{self.API_BASE_URL}/tasks/{task_id}"
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise VideoGenerationError(
                    f"Task timed out after {max_wait_time} seconds",
                    provider=self.provider_name,
                    details={"task_id": task_id},
                )

            try:
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                status = result.get("status", "UNKNOWN")
                self.logger.debug(f"Task {task_id} status: {status}")

                if status == "SUCCEEDED":
                    # Extract video URL from output
                    output = result.get("output", [])
                    if output and len(output) > 0:
                        return output[0]
                    raise VideoGenerationError(
                        "No output URL in completed task",
                        provider=self.provider_name,
                        details={"result": str(result)[:500]},
                    )

                elif status == "FAILED":
                    failure_reason = result.get("failure", "Unknown failure")
                    failure_code = result.get("failureCode", "UNKNOWN")
                    raise VideoGenerationError(
                        f"Runway task failed: {failure_reason} ({failure_code})",
                        provider=self.provider_name,
                        details={"task_id": task_id, "result": str(result)[:500]},
                    )

                elif status in ["PENDING", "RUNNING", "THROTTLED"]:
                    # Task still in progress
                    progress = result.get("progress", 0)
                    self.logger.debug(f"Task progress: {progress:.0%}")
                    time.sleep(poll_interval)

                else:
                    self.logger.warning(f"Unknown task status: {status}")
                    time.sleep(poll_interval)

            except requests.RequestException as e:
                self.logger.warning(f"Polling error (retrying): {e}")
                time.sleep(poll_interval)

    @classmethod
    def get_provider_info(cls) -> Dict[str, Any]:
        """Return metadata about this provider for UI display."""
        return {
            "id": cls.PROVIDER_ID,
            "name": "Runway ML (Gen-3)",
            "description": "High-quality video generation using Gen-3 Alpha Turbo model",
            "valid_durations": cls.VALID_DURATIONS,
            "valid_aspect_ratios": cls.VALID_ASPECT_RATIOS,
            "env_key": cls.ENV_KEY_NAME,
            "default_model": cls.DEFAULT_MODEL,
        }
