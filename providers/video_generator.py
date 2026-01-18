"""
Video generation provider - backward compatibility module.

This module provides backward compatibility by re-exporting
the FalVideoGenerator as VideoGenerator.

For new code, prefer using:
    from providers import create_video_generator
    generator = create_video_generator("fal")  # or "runway", "luma"

Or directly:
    from providers.fal_video_generator import FalVideoGenerator
    from providers.runway_generator import RunwayVideoGenerator
    from providers.luma_generator import LumaVideoGenerator
"""

# Re-export for backward compatibility
from .fal_video_generator import FalVideoGenerator, VideoGenerator

__all__ = ["VideoGenerator", "FalVideoGenerator"]
