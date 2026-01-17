"""
Image generation provider using Replicate API.
Implements the Flux 1.1 Pro model for high-quality image generation.
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any

import replicate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_provider import BaseProvider, ImageGenerationError


class ImageGenerator(BaseProvider):
    """
    Image generation provider using Replicate's Flux 1.1 Pro model.
    
    Generates high-quality photorealistic images for the morphing pipeline.
    """

    DEFAULT_MODEL = "black-forest-labs/flux-1.1-pro"
    VALID_ASPECT_RATIOS = ["1:1", "4:3", "3:4", "16:9", "9:16", "21:9", "9:21"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Replicate image generator.
        
        Args:
            api_key: Replicate API token. If None, reads from REPLICATE_API_TOKEN env var.
            model: Model identifier. Defaults to flux-1.1-pro.
            logger: Optional logger instance.
        """
        self._api_key = api_key or os.environ.get("REPLICATE_API_TOKEN", "")
        self._model = model or self.DEFAULT_MODEL
        super().__init__(self._api_key, logger)

    def _validate_credentials(self) -> None:
        """Validate Replicate API credentials."""
        if not self._api_key:
            raise ImageGenerationError(
                "Replicate API token not configured. Set REPLICATE_API_TOKEN environment variable.",
                provider=self.provider_name,
            )
        # Set the token for the replicate library
        os.environ["REPLICATE_API_TOKEN"] = self._api_key

    @property
    def provider_name(self) -> str:
        return "Replicate"

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((requests.RequestException, Exception)),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        safety_tolerance: int = 2,
    ) -> Path:
        """
        Generate an image using Replicate's Flux model.
        
        Args:
            prompt: The text prompt describing the image to generate.
            output_path: Path where the generated image should be saved.
            aspect_ratio: Aspect ratio of the output image. Default "9:16".
            negative_prompt: Optional negative prompt to avoid certain elements.
            safety_tolerance: Safety filter level (0-6, higher = more permissive).
            
        Returns:
            Path to the saved image file.
            
        Raises:
            ImageGenerationError: If generation fails after retries.
        """
        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            self.logger.warning(
                f"Invalid aspect ratio '{aspect_ratio}', defaulting to '9:16'"
            )
            aspect_ratio = "9:16"

        self.log_api_call(
            "Generating image",
            {"prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt, "aspect_ratio": aspect_ratio},
        )

        start_time = time.time()

        try:
            # Build input parameters
            input_params: Dict[str, Any] = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "output_format": "png",
                "safety_tolerance": safety_tolerance,
            }

            # Run the model
            output = replicate.run(self._model, input=input_params)

            # Handle different output formats
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            elif isinstance(output, str):
                image_url = output
            elif hasattr(output, "url"):
                image_url = output.url
            else:
                # Try to iterate if it's a generator or FileOutput
                try:
                    image_url = str(output)
                except Exception:
                    raise ImageGenerationError(
                        f"Unexpected output format from Replicate: {type(output)}",
                        provider=self.provider_name,
                        details={"output": str(output)[:200]},
                    )

            # Download the image
            self._download_image(image_url, output_path)

            duration = time.time() - start_time
            self.log_api_response("Image generation", success=True, duration=duration)

            self.logger.info(f"Image saved to: {output_path}")
            return output_path

        except replicate.exceptions.ReplicateError as e:
            duration = time.time() - start_time
            self.log_api_response("Image generation", success=False, duration=duration)
            raise ImageGenerationError(
                f"Replicate API error: {str(e)}",
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e
        except Exception as e:
            duration = time.time() - start_time
            self.log_api_response("Image generation", success=False, duration=duration)
            raise ImageGenerationError(
                f"Image generation failed: {str(e)}",
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e

    def _download_image(self, url: str, output_path: Path) -> None:
        """
        Download an image from a URL and save it locally.
        
        Args:
            url: The URL of the image to download.
            output_path: Path where the image should be saved.
            
        Raises:
            ImageGenerationError: If download fails.
        """
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(response.content)

        except requests.RequestException as e:
            raise ImageGenerationError(
                f"Failed to download image from {url}: {str(e)}",
                provider=self.provider_name,
                details={"url": url, "error": str(e)},
            ) from e

    def build_prompt(self, visual_prompt: str, location_prompt: str) -> str:
        """
        Combine visual and location prompts into a complete prompt.
        
        Args:
            visual_prompt: Description of the subject/person.
            location_prompt: Description of the scene/location.
            
        Returns:
            Combined prompt string.
        """
        return f"{visual_prompt}, {location_prompt}"
