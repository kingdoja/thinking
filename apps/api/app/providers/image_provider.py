"""
Image Provider Adapter base class and related types.

This module defines the abstract interface for image generation providers,
allowing the system to support multiple image generation services (Stable Diffusion,
DALL-E, Midjourney, etc.) through a unified interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID


class ProviderError(Exception):
    """
    Exception raised when a provider operation fails.
    
    Attributes:
        message: Human-readable error message
        provider_name: Name of the provider that raised the error
        request_id: Optional request ID from the provider for tracking
        is_retryable: Whether the error is temporary and can be retried
        status_code: HTTP status code if applicable
    """
    
    def __init__(
        self,
        message: str,
        provider_name: str,
        request_id: Optional[str] = None,
        is_retryable: bool = False,
        status_code: Optional[int] = None,
    ):
        self.message = message
        self.provider_name = provider_name
        self.request_id = request_id
        self.is_retryable = is_retryable
        self.status_code = status_code
        super().__init__(self.message)
    
    def __str__(self) -> str:
        parts = [f"[{self.provider_name}] {self.message}"]
        if self.request_id:
            parts.append(f"(request_id: {self.request_id})")
        if self.status_code:
            parts.append(f"(status: {self.status_code})")
        return " ".join(parts)


@dataclass
class ImageGenerationResult:
    """
    Result of an image generation operation.
    
    Attributes:
        success: Whether the generation was successful
        image_data: Binary image data (PNG/JPEG bytes) if successful
        image_url: URL to the generated image if provided by the provider
        width: Width of the generated image in pixels
        height: Height of the generated image in pixels
        format: Image format (e.g., 'png', 'jpeg')
        shot_id: ID of the shot this image was generated for
        provider_metadata: Provider-specific metadata (model version, seed, etc.)
        error: Error message if generation failed
        request_id: Provider's request ID for tracking
        generation_time_ms: Time taken to generate the image in milliseconds
    """
    
    success: bool
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    shot_id: Optional[UUID] = None
    provider_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    generation_time_ms: Optional[int] = None


class ImageProviderAdapter(ABC):
    """
    Abstract base class for image generation provider adapters.
    
    This adapter pattern allows the system to support multiple image generation
    providers (Stable Diffusion, DALL-E, Midjourney, etc.) through a unified
    interface. Each provider implementation handles the specifics of parameter
    conversion, API calls, and response parsing.
    
    Requirements:
    - 3.1: Unified adapter interface for all providers
    - 3.2: Parameter conversion and response normalization
    """
    
    def __init__(self, provider_name: str):
        """
        Initialize the provider adapter.
        
        Args:
            provider_name: Name of the provider (e.g., 'stable_diffusion', 'dalle')
        """
        self.provider_name = provider_name
    
    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1080,
        height: int = 1920,
        style: Optional[str] = None,
        shot_id: Optional[UUID] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate an image based on the provided parameters.
        
        This method must be implemented by each provider adapter to handle
        the specifics of that provider's API.
        
        Args:
            prompt: Positive prompt describing what to generate
            negative_prompt: Negative prompt describing what to avoid
            width: Desired image width in pixels
            height: Desired image height in pixels
            style: Style keywords or preset (provider-specific)
            shot_id: Optional shot ID for tracking
            **kwargs: Provider-specific additional parameters
            
        Returns:
            ImageGenerationResult: Result containing image data or error
            
        Raises:
            ProviderError: If the provider operation fails
        """
        pass
    
    def validate_parameters(
        self,
        prompt: str,
        width: int,
        height: int,
    ) -> None:
        """
        Validate common parameters before making provider call.
        
        Args:
            prompt: The prompt to validate
            width: Image width to validate
            height: Image height to validate
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid dimensions: {width}x{height}")
        
        if width > 4096 or height > 4096:
            raise ValueError(f"Dimensions too large: {width}x{height} (max 4096)")
