"""
Provider adapters for external services.
"""
from .image_provider import (
    ImageProviderAdapter,
    ImageGenerationResult,
    ProviderError,
)
from .stable_diffusion_adapter import StableDiffusionAdapter
from .mock_image_provider import MockImageProvider
from .image_provider_factory import ImageProviderFactory

from .tts_provider import TTSProviderAdapter, TTSResult, TTSProviderError
from .azure_tts_adapter import AzureTTSAdapter
from .mock_tts_provider import MockTTSProvider
from .tts_provider_factory import TTSProviderFactory

__all__ = [
    # Image providers
    "ImageProviderAdapter",
    "ImageGenerationResult",
    "ProviderError",
    "StableDiffusionAdapter",
    "MockImageProvider",
    "ImageProviderFactory",
    # TTS providers
    "TTSProviderAdapter",
    "TTSResult",
    "TTSProviderError",
    "AzureTTSAdapter",
    "MockTTSProvider",
    "TTSProviderFactory",
]
