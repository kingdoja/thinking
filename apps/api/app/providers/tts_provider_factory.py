"""
TTS Provider Factory for creating provider instances.

Implements the Factory pattern to create appropriate TTS provider adapters
based on configuration, allowing easy switching between providers without
modifying business logic.

Requirements:
- 6.5: Provider switching without code changes
"""
from typing import Optional
import logging

from app.core.config import settings
from .tts_provider import TTSProviderAdapter
from .azure_tts_adapter import AzureTTSAdapter
from .mock_tts_provider import MockTTSProvider

logger = logging.getLogger(__name__)


class TTSProviderFactory:
    """
    Factory for creating TTS provider adapter instances.

    Requirements:
    - 6.5: Provider switching without code changes
    """

    _instance: Optional[TTSProviderAdapter] = None

    @classmethod
    def create_provider(
        cls,
        provider_type: Optional[str] = None,
        **override_params,
    ) -> TTSProviderAdapter:
        """
        Create a TTS provider adapter instance.

        Args:
            provider_type: Type of provider to create (overrides config).
                           Supported values: 'azure', 'mock'.
            **override_params: Parameters to override from config.

        Returns:
            TTSProviderAdapter instance

        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = provider_type or settings.tts_provider

        logger.info(f"Creating TTS provider: {provider_type}")

        if provider_type == "azure":
            return cls._create_azure(**override_params)
        elif provider_type == "mock":
            return cls._create_mock(**override_params)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider_type}")

    @classmethod
    def get_provider(cls) -> TTSProviderAdapter:
        """
        Get or create a singleton provider instance.

        Returns:
            TTSProviderAdapter instance
        """
        if cls._instance is None:
            cls._instance = cls.create_provider()
        return cls._instance

    @classmethod
    def reset_provider(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Private factory methods
    # ------------------------------------------------------------------

    @classmethod
    def _create_azure(cls, **override_params) -> AzureTTSAdapter:
        """
        Create Azure TTS adapter with configuration from settings.

        Args:
            **override_params: Parameters to override from config

        Returns:
            AzureTTSAdapter instance
        """
        params = {
            "subscription_key": settings.tts_azure_subscription_key,
            "region": settings.tts_azure_region,
            "default_voice": settings.tts_default_voice,
            "output_format": settings.tts_output_format,
            "timeout": settings.tts_timeout,
            "max_retries": settings.tts_max_retries,
        }
        params.update(override_params)
        return AzureTTSAdapter(**params)

    @classmethod
    def _create_mock(cls, **override_params) -> MockTTSProvider:
        """
        Create mock TTS provider for testing.

        Args:
            **override_params: Parameters to override defaults

        Returns:
            MockTTSProvider instance
        """
        return MockTTSProvider(**override_params)
