"""
Image Generator - Replicate API Wrapper
Generates high-quality images using Flux and other models via Replicate.
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Callable

try:
    import replicate
except ImportError:
    replicate = None

logger = logging.getLogger(__name__)


class ImageGenerator:
    """
    Generates images using Replicate's API.
    
    Supports multiple models:
    - black-forest-labs/flux-1.1-pro (default, best quality)
    - black-forest-labs/flux-schnell (faster, lower quality)
    - stability-ai/sdxl
    """
    
    ASPECT_RATIO_MAP = {
        "9:16": {"width": 768, "height": 1344},
        "16:9": {"width": 1344, "height": 768},
        "1:1": {"width": 1024, "height": 1024},
        "4:3": {"width": 1024, "height": 768},
        "3:4": {"width": 768, "height": 1024},
    }
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        model: str = "black-forest-labs/flux-1.1-pro"
    ):
        """
        Initialize the image generator.
        
        Args:
            api_token: Replicate API token. If None, reads from REPLICATE_API_TOKEN env.
            model: The model identifier to use for generation.
        """
        self.api_token = api_token or os.environ.get("REPLICATE_API_TOKEN")
        self.model = model
        
        if not self.api_token:
            raise ValueError(
                "Replicate API token required. Set REPLICATE_API_TOKEN environment variable "
                "or pass api_token to constructor."
            )
        
        if replicate is None:
            raise ImportError("replicate package not installed. Run: pip install replicate")
        
        # Set token for replicate client
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        
        logger.info(f"ImageGenerator initialized with model: {self.model}")
    
    def _get_dimensions(self, aspect_ratio: str) -> Dict[str, int]:
        """Get width/height for the given aspect ratio."""
        return self.ASPECT_RATIO_MAP.get(aspect_ratio, self.ASPECT_RATIO_MAP["9:16"])
    
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "9:16",
        output_path: Optional[Path] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: The text prompt describing the desired image.
            negative_prompt: Things to avoid in the image.
            aspect_ratio: The aspect ratio (e.g., "9:16", "16:9", "1:1").
            output_path: Optional path to save the image. If None, returns URL.
            on_progress: Optional callback for progress updates.
            
        Returns:
            The URL of the generated image, or the local file path if output_path is provided.
        """
        dimensions = self._get_dimensions(aspect_ratio)
        
        if on_progress:
            on_progress(f"Generating image with {self.model}...")
        
        logger.info(f"Generating image: '{prompt[:50]}...' at {aspect_ratio}")
        
        # Build input parameters based on model
        if "flux" in self.model.lower():
            input_params = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "output_format": "png",
                "output_quality": 100,
            }
            if negative_prompt:
                input_params["negative_prompt"] = negative_prompt
        else:
            # SDXL-style models
            input_params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt or "blurry, low quality",
                "width": dimensions["width"],
                "height": dimensions["height"],
            }
        
        try:
            # Run the model
            output = replicate.run(self.model, input=input_params)
            
            # Handle different output formats
            if isinstance(output, list):
                image_url = output[0] if output else None
            elif isinstance(output, str):
                image_url = output
            else:
                # FileOutput object
                image_url = str(output)
            
            if not image_url:
                raise RuntimeError("No image URL returned from Replicate")
            
            logger.info(f"Image generated: {image_url}")
            
            # Download if output path specified
            if output_path:
                if on_progress:
                    on_progress(f"Downloading to {output_path}...")
                
                self._download_image(image_url, output_path)
                return str(output_path)
            
            return image_url
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
    
    def _download_image(self, url: str, output_path: Path) -> None:
        """Download an image from URL to local path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Image saved to: {output_path}")
    
    def generate_subject(
        self,
        subject_name: str,
        visual_prompt: str,
        location_prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "9:16",
        output_path: Optional[Path] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Generate an image of a subject in a scene.
        
        Combines the subject's visual prompt with the global location prompt.
        
        Args:
            subject_name: Name of the subject (for logging).
            visual_prompt: Description of the subject's appearance.
            location_prompt: Description of the scene/location.
            negative_prompt: Things to avoid.
            aspect_ratio: The aspect ratio.
            output_path: Optional path to save the image.
            on_progress: Optional progress callback.
            
        Returns:
            URL or file path of the generated image.
        """
        # Combine prompts for a cohesive image
        full_prompt = f"{visual_prompt}, {location_prompt}"
        
        if on_progress:
            on_progress(f"Generating {subject_name}...")
        
        return self.generate(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            output_path=output_path,
            on_progress=on_progress
        )
