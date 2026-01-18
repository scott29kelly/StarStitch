"""
StarStitch Providers Module
Contains AI provider implementations for image and video generation.

Video Provider Architecture:
- BaseVideoGenerator: Abstract base class for all video providers
- FalVideoGenerator: Fal.ai/Kling implementation
- RunwayVideoGenerator: Runway ML Gen-3 implementation  
- LumaVideoGenerator: Luma Dream Machine implementation
- VideoProviderFactory: Factory for provider creation
- create_video_generator: Convenience function for creating generators

Usage:
    # Recommended approach - use factory
    from providers import create_video_generator
    generator = create_video_generator("luma")
    
    # Or get specific provider class
    from providers import RunwayVideoGenerator
    generator = RunwayVideoGenerator()
    
    # Legacy import still works
    from providers import VideoGenerator  # Defaults to FalVideoGenerator
"""

from .base_provider import BaseProvider, ProviderError, ImageGenerationError, VideoGenerationError
from .base_video_generator import BaseVideoGenerator
from .image_generator import ImageGenerator

# Video generators
from .fal_video_generator import FalVideoGenerator
from .runway_generator import RunwayVideoGenerator
from .luma_generator import LumaVideoGenerator

# Factory and convenience function
from .video_provider_factory import VideoProviderFactory, create_video_generator

# Backward compatibility alias
from .video_generator import VideoGenerator

__all__ = [
    # Base classes
    "BaseProvider",
    "BaseVideoGenerator",
    "ProviderError",
    "ImageGenerationError",
    "VideoGenerationError",
    # Image generator
    "ImageGenerator",
    # Video generators
    "VideoGenerator",  # Backward compat (FalVideoGenerator)
    "FalVideoGenerator",
    "RunwayVideoGenerator",
    "LumaVideoGenerator",
    # Factory
    "VideoProviderFactory",
    "create_video_generator",
]
