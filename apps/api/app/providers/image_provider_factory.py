"""
Image Provider Factory for creating provider instances.

This factory implements the Factory pattern to create appropriate provider
adapters based on configuration, allowing easy switching between providers
without modifying business logic.
"""
from typing import Optional
import logging

from app.core.config import settings
from .image_provider import ImageProviderAdapter
from .stable_diffusion_adapter import StableDiffusionAdapter
from .mock_image_provider import MockImageProvider

logger = logging.getLogger(__name__)


class ImageProviderFactory:
    """
    Factory for creating image provider adapter instances.
    
    Requirements:
    - 3.5: Provider switching without code changes
    """
    
    _instance: Optional[ImageProviderAdapter] = None
    
    @classmethod
    def create_provider(
        cls,
        provider_type: Optional[str] = None,
        **override_params
    ) -> ImageProviderAdapter:
        """
        Create an image provider adapter instance.
        
        Args:
            provider_type: Type of provider to create (overrides config)
            **override_params: Parameters to override from config
            
        Returns:
            ImageProviderAdapter instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = provider_type or settings.image_provider
        
        logger.info(f"Creating image provider: {provider_type}")
        
        if provider_type == "stable_diffusion":
            return cls._create_stable_diffusion(**override_params)
        elif provider_type == "mock":
            return cls._create_mock(**override_params)
        else:
            raise ValueError(f"Unsupported image provider: {provider_type}")
    
    @classmethod
    def get_provider(cls) -> ImageProviderAdapter:
        """
        Get or create a singleton provider instance.
        
        Returns:
            ImageProviderAdapter instance
        """
        if cls._instance is None:
            cls._instance = cls.create_provider()
        return cls._instance
    
    @classmethod
    def reset_provider(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
    
    @classmethod
    def _create_stable_diffusion(cls, **override_params) -> StableDiffusionAdapter:
        """
        Create Stable Diffusion adapter with configuration.
        
        Args:
            **override_params: Parameters to override from config
            
        Returns:
            StableDiffusionAdapter instance
        """
        params = {
            "api_url": settings.image_provider_api_url,
            "api_key": settings.image_provider_api_key or None,
            "model": settings.image_provider_model,
            "timeout": settings.image_provider_timeout,
            "max_retries": settings.image_provider_max_retries,
        }
        params.update(override_params)
        
        return StableDiffusionAdapter(**params)
    
    @classmethod
    def _create_mock(cls, **override_params) -> MockImageProvider:
        """
        Create mock provider for testing.
        
        Args:
            **override_params: Parameters to override defaults
            
        Returns:
            MockImageProvider instance
        """
        return MockImageProvider(**override_params)
