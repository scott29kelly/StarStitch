"""
Video generation provider using Replicate API.
Implements Google Veo 3.1 Fast for image-to-video morphing.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    import replicate
except ImportError:
    replicate = None

from .base_video_generator import BaseVideoGenerator
from .base_provider import VideoGenerationError


class ReplicateVideoGenerator(BaseVideoGenerator):
    """
    Video generation provider using Replicate's hosted models.

    Uses Google Veo 3.1 Fast for fast, high-quality morphing transitions
    between two images. Supports start image + last_frame for true morphing.

    Key advantages:
    - Uses existing REPLICATE_API_TOKEN (no new API key needed)
    - ~62 seconds per video generation
    - True morphing via image + last_frame parameters

    API Documentation: https://replicate.com/google/veo-3.1-fast
    """

    PROVIDER_ID = "replicate"
    DEFAULT_MODEL = "google/veo-3.1-fast"
    VALID_ASPECT_RATIOS = ["16:9", "9:16"]  # Veo 3.1 supports these
    VALID_DURATIONS = ["4", "6", "8"]  # Veo 3.1 duration options
    ENV_KEY_NAME = "REPLICATE_API_TOKEN"

    # Models that are valid for Replicate (ignore Fal.ai/Kling model strings)
    VALID_MODELS = [
        "google/veo-3.1-fast",
        "google/veo-3.1",
        "google/veo-3",
        "google/veo-3-fast",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize with model validation to ignore incompatible model strings."""
        # Validate model - ignore Fal.ai/Kling/Luma model strings that don't work with Replicate
        if model and ("fal-ai" in model or "kling" in model.lower() or "luma" in model.lower()):
            log = logger or logging.getLogger(__name__)
            log.warning(f"Ignoring incompatible model '{model}', using default: {self.DEFAULT_MODEL}")
            model = None

        super().__init__(api_key=api_key, model=model, logger=logger)

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_name(self) -> str:
        return "Replicate (Veo 3.1 Fast)"

    def _get_default_api_key(self) -> str:
        return os.environ.get(self.ENV_KEY_NAME, "")

    def _validate_credentials(self) -> None:
        """Validate Replicate API credentials."""
        if not self._api_key:
            raise VideoGenerationError(
                f"Replicate API token not configured. Set {self.ENV_KEY_NAME} environment variable.",
                provider=self.provider_name,
            )
        if replicate is None:
            raise VideoGenerationError(
                "replicate package not installed. Run: pip install replicate",
                provider=self.provider_name,
            )
        # Set the token for the replicate library
        os.environ[self.ENV_KEY_NAME] = self._api_key

    def _map_duration(self, duration: str) -> int:
        """
        Map requested duration to closest valid Veo 3.1 duration.

        Veo 3.1 supports: 4, 6, 8 seconds
        StarStitch typically uses: 5 or 10 seconds

        Mapping:
        - 2-4 -> 4
        - 5-6 -> 6
        - 7-10 -> 8
        """
        try:
            dur = int(duration)
        except ValueError:
            dur = 6  # Default

        if dur <= 4:
            return 4
        elif dur <= 6:
            return 6
        else:
            return 8

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    def generate(
        self,
        start_image_path: Path,
        end_image_path: Path,
        output_path: Path,
        prompt: str = "smooth morphing transition between two subjects",
        duration: str = "5",
        aspect_ratio: str = "9:16",
    ) -> Path:
        """
        Generate a morphing video between two images using Veo 3.1 Fast.

        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            output_path: Path where the generated video should be saved.
            prompt: Transition description prompt.
            duration: Video duration in seconds (will be mapped to 4, 6, or 8).
            aspect_ratio: Aspect ratio of the output video.

        Returns:
            Path to the saved video file.

        Raises:
            VideoGenerationError: If generation fails after retries.
        """
        self._validate_credentials()

        # Validate inputs - use parent's validation but override duration mapping
        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            self.logger.warning(f"Invalid aspect ratio '{aspect_ratio}', defaulting to '9:16'")
            aspect_ratio = "9:16"

        # Verify input files exist
        if not Path(start_image_path).exists():
            raise VideoGenerationError(
                f"Start image not found: {start_image_path}",
                provider=self.provider_name,
            )
        if not Path(end_image_path).exists():
            raise VideoGenerationError(
                f"End image not found: {end_image_path}",
                provider=self.provider_name,
            )

        # Map duration to valid Veo 3.1 value
        mapped_duration = self._map_duration(duration)

        self.log_api_call(
            "Generating morph video",
            {
                "start_image": str(Path(start_image_path).name),
                "end_image": str(Path(end_image_path).name),
                "duration": mapped_duration,
                "aspect_ratio": aspect_ratio,
                "model": self._model,
            },
        )

        start_time = time.time()

        try:
            self.logger.info(f"Submitting to Replicate ({self._model})...")
            self.logger.info(f"Duration: {mapped_duration}s, Aspect ratio: {aspect_ratio}")

            # Open image files for upload
            with open(start_image_path, "rb") as start_file, open(end_image_path, "rb") as end_file:
                # Call Replicate API with image + last_frame for morphing
                output = replicate.run(
                    self._model,
                    input={
                        "prompt": prompt,
                        "image": start_file,
                        "last_frame": end_file,
                        "duration": mapped_duration,
                        "aspect_ratio": aspect_ratio,
                        "generate_audio": False,  # No audio for morph clips
                        "resolution": "720p",  # Faster than 1080p
                    }
                )

            # Replicate returns the video URL (or file output)
            if isinstance(output, str):
                video_url = output
            elif hasattr(output, 'url'):
                video_url = output.url
            elif isinstance(output, list) and len(output) > 0:
                video_url = output[0] if isinstance(output[0], str) else output[0].url
            else:
                raise VideoGenerationError(
                    f"Unexpected output format from Replicate: {type(output)}",
                    provider=self.provider_name,
                    details={"output": str(output)[:500]},
                )

            # Download the video
            self.download_video(video_url, output_path)

            duration_elapsed = time.time() - start_time
            self.log_api_response("Video generation", success=True, duration=duration_elapsed)

            self.logger.info(f"Video saved to: {output_path} ({duration_elapsed:.1f}s)")
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

        This method matches the interface expected by StarStitchPipeline.

        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            duration_seconds: Duration of the morph video (will be mapped to 4, 6, or 8).
            aspect_ratio: The aspect ratio.
            output_path: Path to save the video.
            on_progress: Optional progress callback.

        Returns:
            Path to the generated video file.
        """
        if on_progress:
            on_progress(f"Generating {duration_seconds}s morph with Veo 3.1 Fast...")

        # Call the generate method
        result = self.generate(
            start_image_path=Path(start_image_path),
            end_image_path=Path(end_image_path),
            output_path=Path(output_path) if output_path else Path("output.mp4"),
            prompt="smooth morphing transition, natural movement",
            duration=str(duration_seconds),
            aspect_ratio=aspect_ratio,
        )

        if on_progress:
            on_progress(f"Morph video saved to {result}")

        return str(result)

    @classmethod
    def get_provider_info(cls) -> Dict[str, Any]:
        """Return metadata about this provider for UI display."""
        return {
            "id": cls.PROVIDER_ID,
            "name": "Replicate (Veo 3.1 Fast)",
            "description": "Fast video morphing using Google Veo 3.1 Fast via Replicate (~62s/video)",
            "valid_durations": cls.VALID_DURATIONS,
            "valid_aspect_ratios": cls.VALID_ASPECT_RATIOS,
            "env_key": cls.ENV_KEY_NAME,
            "default_model": cls.DEFAULT_MODEL,
        }
