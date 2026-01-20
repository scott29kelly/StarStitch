"""
Abstract base class for video generation providers.
Defines the interface that all video providers must implement.
"""

from abc import abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import time
import requests

from .base_provider import BaseProvider, VideoGenerationError


class BaseVideoGenerator(BaseProvider):
    """
    Abstract base class for video generation providers.
    
    All video generator implementations must inherit from this class
    and implement the required abstract methods.
    
    This abstraction allows StarStitch to support multiple video
    backends (Fal.ai/Kling, Runway, Luma, etc.) with a unified interface.
    """

    # Valid configuration options - subclasses can override
    VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16"]
    VALID_DURATIONS = ["5", "10"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the video generator.
        
        Args:
            api_key: API key for the provider. If None, reads from env var.
            model: Model identifier. Defaults to provider's default model.
            logger: Optional logger instance.
        """
        self._api_key = api_key or self._get_default_api_key()
        self._model = model or self.default_model
        super().__init__(self._api_key, logger)

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model identifier for this provider."""
        pass

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """
        Return a unique identifier for this provider.
        Used in config files and factory selection.
        e.g., 'fal', 'runway', 'luma'
        """
        pass

    @abstractmethod
    def _get_default_api_key(self) -> str:
        """
        Get the default API key from environment variables.
        
        Returns:
            The API key string, or empty string if not found.
        """
        pass

    @abstractmethod
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
        Generate a morphing video between two images.
        
        This is the core method that all video providers must implement.
        
        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            output_path: Path where the generated video should be saved.
            prompt: Transition description prompt.
            duration: Video duration in seconds (as string: "5" or "10").
            aspect_ratio: Aspect ratio of the output video.
            
        Returns:
            Path to the saved video file.
            
        Raises:
            VideoGenerationError: If generation fails after retries.
        """
        pass

    def validate_inputs(
        self,
        start_image_path: Path,
        end_image_path: Path,
        duration: str,
        aspect_ratio: str,
    ) -> tuple[str, str]:
        """
        Validate input parameters and paths.
        
        Args:
            start_image_path: Path to the starting image.
            end_image_path: Path to the ending image.
            duration: Requested video duration.
            aspect_ratio: Requested aspect ratio.
            
        Returns:
            Tuple of (validated_duration, validated_aspect_ratio).
            
        Raises:
            VideoGenerationError: If input files don't exist.
        """
        # Validate duration
        if duration not in self.VALID_DURATIONS:
            self.logger.warning(f"Invalid duration '{duration}', defaulting to '5'")
            duration = "5"

        # Validate aspect ratio
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

        return duration, aspect_ratio

    def download_video(self, url: str, output_path: Path) -> None:
        """
        Download a video from a URL and save it locally.
        
        Shared utility method for all video providers.
        
        Args:
            url: The URL of the video to download.
            output_path: Path where the video should be saved.
            
        Raises:
            VideoGenerationError: If download fails.
        """
        try:
            self.logger.info(f"Downloading video from {self.provider_name}...")
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

    @property
    def model_name(self) -> str:
        """Return the current model being used."""
        return self._model

    @classmethod
    def get_provider_info(cls) -> Dict[str, Any]:
        """
        Return metadata about this provider for UI display.
        
        Override in subclasses to provide specific info.
        """
        return {
            "id": getattr(cls, "PROVIDER_ID", "unknown"),
            "name": cls.__name__,
            "description": cls.__doc__ or "No description available",
            "valid_durations": cls.VALID_DURATIONS,
            "valid_aspect_ratios": cls.VALID_ASPECT_RATIOS,
        }
