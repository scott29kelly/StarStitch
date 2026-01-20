"""
Video generation provider using Luma AI Dream Machine API.
Implements the Dream Machine model for image-to-video morphing.
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_video_generator import BaseVideoGenerator
from .base_provider import VideoGenerationError


class LumaVideoGenerator(BaseVideoGenerator):
    """
    Video generation provider using Luma AI's Dream Machine model.
    
    Generates smooth, cinematic morphing transitions between two images
    using Luma's Dream Machine, known for its photorealistic output
    and smooth motion quality.
    
    API Documentation: https://docs.lumalabs.ai/
    """

    PROVIDER_ID = "luma"
    DEFAULT_MODEL = "luma-dream-machine"
    VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "9:21"]
    VALID_DURATIONS = ["5", "9"]  # Luma supports ~5s and ~9s generations
    ENV_KEY_NAME = "LUMA_API_KEY"
    
    API_BASE_URL = "https://api.lumalabs.ai/dream-machine/v1"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_name(self) -> str:
        return "Luma AI"

    def _get_default_api_key(self) -> str:
        return os.environ.get(self.ENV_KEY_NAME, "")

    def _validate_credentials(self) -> None:
        """Validate Luma AI API credentials."""
        if not self._api_key:
            raise VideoGenerationError(
                f"Luma AI API key not configured. Set {self.ENV_KEY_NAME} environment variable.",
                provider=self.provider_name,
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Luma API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _upload_image(self, image_path: Path) -> str:
        """
        Upload an image to Luma's storage and get a signed URL.
        
        Luma requires images to be accessible via URL, so we upload
        them to their temporary storage first.
        
        Args:
            image_path: Path to the local image file.
            
        Returns:
            URL of the uploaded image.
            
        Raises:
            VideoGenerationError: If upload fails.
        """
        # First, get an upload URL from Luma
        try:
            # Request an upload URL
            response = requests.post(
                f"{self.API_BASE_URL}/generations/file-upload",
                headers=self._get_headers(),
                json={"type": "image"},
                timeout=30,
            )
            response.raise_for_status()
            upload_data = response.json()
            
            presigned_url = upload_data.get("presigned_url")
            public_url = upload_data.get("public_url")
            
            if not presigned_url:
                raise VideoGenerationError(
                    "Failed to get presigned URL from Luma",
                    provider=self.provider_name,
                    details={"response": str(upload_data)[:500]},
                )
            
            # Upload the image to the presigned URL
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Determine content type
            extension = image_path.suffix.lower()
            content_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }
            content_type = content_types.get(extension, "image/png")
            
            upload_response = requests.put(
                presigned_url,
                data=image_data,
                headers={"Content-Type": content_type},
                timeout=60,
            )
            upload_response.raise_for_status()
            
            self.logger.debug(f"Image uploaded to Luma: {public_url}")
            return public_url
            
        except requests.RequestException as e:
            raise VideoGenerationError(
                f"Failed to upload image to Luma: {str(e)}",
                provider=self.provider_name,
                details={"image_path": str(image_path), "error": str(e)},
            ) from e

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
        Generate a morphing video between two images using Luma's Dream Machine.
        
        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            output_path: Path where the generated video should be saved.
            prompt: Transition description prompt.
            duration: Video duration in seconds ("5" or "9").
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
        
        # Map duration to Luma's supported values
        if duration == "10":
            duration = "9"  # Luma max is ~9 seconds

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
            # Upload images to Luma storage
            self.logger.info("Uploading start image to Luma storage...")
            start_image_url = self._upload_image(start_image_path)

            self.logger.info("Uploading end image to Luma storage...")
            end_image_url = self._upload_image(end_image_path)

            # Create the generation task
            generation_id = self._create_generation(
                start_image_url=start_image_url,
                end_image_url=end_image_url,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )

            self.logger.info(f"Generation created: {generation_id}, polling for completion...")

            # Poll for completion
            video_url = self._poll_for_completion(generation_id)

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

    def _create_generation(
        self,
        start_image_url: str,
        end_image_url: str,
        prompt: str,
        aspect_ratio: str,
    ) -> str:
        """
        Create a video generation request on Luma.
        
        Args:
            start_image_url: URL of the start image.
            end_image_url: URL of the end image.
            prompt: Text prompt for the transition.
            aspect_ratio: Aspect ratio string.
            
        Returns:
            Generation ID for polling.
            
        Raises:
            VideoGenerationError: If creation fails.
        """
        url = f"{self.API_BASE_URL}/generations"
        
        # Build the request payload for image-to-video with keyframes
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "keyframes": {
                "frame0": {
                    "type": "image",
                    "url": start_image_url,
                },
                "frame1": {
                    "type": "image",
                    "url": end_image_url,
                },
            },
        }

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            
            result = response.json()
            generation_id = result.get("id")
            
            if not generation_id:
                raise VideoGenerationError(
                    f"No generation ID in Luma response: {result}",
                    provider=self.provider_name,
                    details={"response": str(result)[:500]},
                )
            
            return generation_id
            
        except requests.RequestException as e:
            error_detail = ""
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text[:500]
            
            raise VideoGenerationError(
                f"Failed to create Luma generation: {str(e)}",
                provider=self.provider_name,
                details={"error": str(e), "response": error_detail},
            ) from e

    def _poll_for_completion(
        self,
        generation_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 5,
    ) -> str:
        """
        Poll the Luma API until the generation completes.
        
        Args:
            generation_id: The generation ID to poll.
            max_wait_time: Maximum time to wait in seconds.
            poll_interval: Time between polls in seconds.
            
        Returns:
            URL of the generated video.
            
        Raises:
            VideoGenerationError: If generation fails or times out.
        """
        url = f"{self.API_BASE_URL}/generations/{generation_id}"
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise VideoGenerationError(
                    f"Generation timed out after {max_wait_time} seconds",
                    provider=self.provider_name,
                    details={"generation_id": generation_id},
                )

            try:
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                state = result.get("state", "unknown")
                self.logger.debug(f"Generation {generation_id} state: {state}")

                if state == "completed":
                    # Extract video URL from assets
                    assets = result.get("assets", {})
                    video_url = assets.get("video")
                    
                    if not video_url:
                        raise VideoGenerationError(
                            "No video URL in completed generation",
                            provider=self.provider_name,
                            details={"result": str(result)[:500]},
                        )
                    
                    return video_url

                elif state == "failed":
                    failure_reason = result.get("failure_reason", "Unknown failure")
                    raise VideoGenerationError(
                        f"Luma generation failed: {failure_reason}",
                        provider=self.provider_name,
                        details={"generation_id": generation_id, "result": str(result)[:500]},
                    )

                elif state in ["queued", "dreaming", "processing"]:
                    # Generation still in progress
                    self.logger.debug(f"Generation state: {state}")
                    time.sleep(poll_interval)

                else:
                    self.logger.warning(f"Unknown generation state: {state}")
                    time.sleep(poll_interval)

            except requests.RequestException as e:
                self.logger.warning(f"Polling error (retrying): {e}")
                time.sleep(poll_interval)

    @classmethod
    def get_provider_info(cls) -> Dict[str, Any]:
        """Return metadata about this provider for UI display."""
        return {
            "id": cls.PROVIDER_ID,
            "name": "Luma AI (Dream Machine)",
            "description": "Cinematic video generation using Luma's Dream Machine model",
            "valid_durations": cls.VALID_DURATIONS,
            "valid_aspect_ratios": cls.VALID_ASPECT_RATIOS,
            "env_key": cls.ENV_KEY_NAME,
            "default_model": cls.DEFAULT_MODEL,
        }
