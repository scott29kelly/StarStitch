"""
Abstract base class for AI providers.
Provides common interface and shared functionality for all providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, provider: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class ImageGenerationError(ProviderError):
    """Exception for image generation failures."""

    pass


class VideoGenerationError(ProviderError):
    """Exception for video generation failures."""

    pass


class BaseProvider(ABC):
    """
    Abstract base class for AI providers.
    
    All provider implementations must inherit from this class
    and implement the required abstract methods.
    """

    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the provider.
        
        Args:
            api_key: The API key for authentication
            logger: Optional logger instance
        """
        self.api_key = api_key
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._validate_credentials()

    @abstractmethod
    def _validate_credentials(self) -> None:
        """
        Validate that the API credentials are properly configured.
        Should raise an exception if credentials are invalid.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model being used by this provider."""
        pass

    def get_retry_decorator(self, max_attempts: int = 3):
        """
        Get a retry decorator with exponential backoff.
        
        Args:
            max_attempts: Maximum number of retry attempts
            
        Returns:
            A tenacity retry decorator
        """
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((Exception,)),
            before_sleep=before_sleep_log(self.logger, logging.WARNING),
            reraise=True,
        )

    def log_api_call(self, operation: str, details: Dict[str, Any]) -> None:
        """
        Log an API call with relevant details.
        
        Args:
            operation: Description of the operation
            details: Dictionary of operation details
        """
        self.logger.info(
            f"[{self.provider_name}] {operation}",
            extra={"provider": self.provider_name, "details": details},
        )

    def log_api_response(
        self, operation: str, success: bool, duration: float, cost: Optional[float] = None
    ) -> None:
        """
        Log an API response with timing and optional cost.
        
        Args:
            operation: Description of the operation
            success: Whether the operation succeeded
            duration: Time taken in seconds
            cost: Optional cost in USD
        """
        status = "SUCCESS" if success else "FAILED"
        cost_str = f", cost=${cost:.4f}" if cost else ""
        self.logger.info(
            f"[{self.provider_name}] {operation} - {status} ({duration:.2f}s{cost_str})"
        )
