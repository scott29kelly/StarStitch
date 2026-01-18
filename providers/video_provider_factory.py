"""
Factory for creating video generator instances.
Provides a registry pattern for easy provider selection and extension.
"""

import logging
from typing import Dict, Type, Optional, List, Any

from .base_video_generator import BaseVideoGenerator
from .base_provider import VideoGenerationError
from .fal_video_generator import FalVideoGenerator
from .runway_generator import RunwayVideoGenerator
from .luma_generator import LumaVideoGenerator


class VideoProviderFactory:
    """
    Factory class for creating video generator instances.
    
    Implements a registry pattern that allows:
    - Easy provider selection by ID (e.g., "fal", "runway", "luma")
    - Runtime provider registration for extensibility
    - Provider discovery and metadata querying
    
    Usage:
        # Get a provider by ID
        generator = VideoProviderFactory.create("fal")
        
        # Get provider with custom config
        generator = VideoProviderFactory.create(
            provider_id="runway",
            api_key="your-key",
            model="gen3a_turbo"
        )
        
        # List available providers
        providers = VideoProviderFactory.list_providers()
    """

    # Registry of available providers
    _registry: Dict[str, Type[BaseVideoGenerator]] = {}

    @classmethod
    def register(cls, provider_id: str, provider_class: Type[BaseVideoGenerator]) -> None:
        """
        Register a new video provider.
        
        Args:
            provider_id: Unique identifier for the provider (e.g., "fal", "runway").
            provider_class: The provider class (must inherit from BaseVideoGenerator).
            
        Raises:
            TypeError: If provider_class doesn't inherit from BaseVideoGenerator.
        """
        if not issubclass(provider_class, BaseVideoGenerator):
            raise TypeError(
                f"Provider class must inherit from BaseVideoGenerator, got {provider_class}"
            )
        cls._registry[provider_id] = provider_class

    @classmethod
    def create(
        cls,
        provider_id: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> BaseVideoGenerator:
        """
        Create a video generator instance by provider ID.
        
        Args:
            provider_id: The provider identifier (e.g., "fal", "runway", "luma").
            api_key: Optional API key. If None, provider reads from env vars.
            model: Optional model identifier. If None, uses provider default.
            logger: Optional logger instance.
            
        Returns:
            An instance of the requested video generator.
            
        Raises:
            VideoGenerationError: If provider_id is not registered.
        """
        provider_id = provider_id.lower()
        
        if provider_id not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise VideoGenerationError(
                f"Unknown video provider: '{provider_id}'. Available providers: {available}",
                provider="VideoProviderFactory",
                details={"requested": provider_id, "available": list(cls._registry.keys())},
            )
        
        provider_class = cls._registry[provider_id]
        return provider_class(api_key=api_key, model=model, logger=logger)

    @classmethod
    def get_provider_class(cls, provider_id: str) -> Type[BaseVideoGenerator]:
        """
        Get the provider class for a given provider ID.
        
        Args:
            provider_id: The provider identifier.
            
        Returns:
            The provider class.
            
        Raises:
            VideoGenerationError: If provider_id is not registered.
        """
        provider_id = provider_id.lower()
        
        if provider_id not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise VideoGenerationError(
                f"Unknown video provider: '{provider_id}'. Available: {available}",
                provider="VideoProviderFactory",
            )
        
        return cls._registry[provider_id]

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all registered provider IDs.
        
        Returns:
            List of provider ID strings.
        """
        return sorted(cls._registry.keys())

    @classmethod
    def get_provider_info(cls, provider_id: str) -> Dict[str, Any]:
        """
        Get metadata about a specific provider.
        
        Args:
            provider_id: The provider identifier.
            
        Returns:
            Dictionary of provider metadata.
        """
        provider_class = cls.get_provider_class(provider_id)
        return provider_class.get_provider_info()

    @classmethod
    def get_all_provider_info(cls) -> List[Dict[str, Any]]:
        """
        Get metadata for all registered providers.
        
        Returns:
            List of provider metadata dictionaries.
        """
        return [
            cls.get_provider_info(provider_id)
            for provider_id in cls.list_providers()
        ]

    @classmethod
    def is_registered(cls, provider_id: str) -> bool:
        """
        Check if a provider ID is registered.
        
        Args:
            provider_id: The provider identifier to check.
            
        Returns:
            True if the provider is registered, False otherwise.
        """
        return provider_id.lower() in cls._registry


# Auto-register built-in providers
VideoProviderFactory.register("fal", FalVideoGenerator)
VideoProviderFactory.register("kling", FalVideoGenerator)  # Alias for fal
VideoProviderFactory.register("runway", RunwayVideoGenerator)
VideoProviderFactory.register("luma", LumaVideoGenerator)


def create_video_generator(
    provider: str = "fal",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> BaseVideoGenerator:
    """
    Convenience function to create a video generator.
    
    This is the recommended way to get a video generator instance.
    
    Args:
        provider: Provider ID ("fal", "runway", "luma", etc.).
        api_key: Optional API key for the provider.
        model: Optional model identifier.
        logger: Optional logger instance.
        
    Returns:
        A configured video generator instance.
        
    Example:
        >>> generator = create_video_generator("luma")
        >>> generator.generate(start_img, end_img, output)
    """
    return VideoProviderFactory.create(
        provider_id=provider,
        api_key=api_key,
        model=model,
        logger=logger,
    )
