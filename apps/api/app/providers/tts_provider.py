"""
TTS Provider Adapter base class and related types.

This module defines the abstract interface for text-to-speech providers,
allowing the system to support multiple TTS services (Azure TTS, Google TTS,
ElevenLabs, etc.) through a unified interface.

Requirements:
- 6.1: Unified adapter interface for all TTS providers
- 6.2: Parameter conversion and response normalization
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from uuid import UUID


class TTSProviderError(Exception):
    """
    Exception raised when a TTS provider operation fails.

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
class TTSResult:
    """
    Result of a text-to-speech synthesis operation.

    Attributes:
        success: Whether the synthesis was successful
        audio_data: Binary audio data (MP3/WAV bytes) if successful
        audio_format: Audio format (e.g., 'mp3', 'wav', 'ogg')
        duration_ms: Duration of the audio in milliseconds
        sample_rate: Sample rate of the audio in Hz
        channels: Number of audio channels (1=mono, 2=stereo)
        shot_id: ID of the shot this audio was generated for
        provider_metadata: Provider-specific metadata
        error: Error message if synthesis failed
        request_id: Provider's request ID for tracking
        synthesis_time_ms: Time taken to synthesize in milliseconds
        character_count: Number of characters synthesized (for cost tracking)
    """

    success: bool
    audio_data: Optional[bytes] = None
    audio_format: Optional[str] = None
    duration_ms: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    shot_id: Optional[UUID] = None
    provider_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    synthesis_time_ms: Optional[int] = None
    character_count: Optional[int] = None


class TTSProviderAdapter(ABC):
    """
    Abstract base class for text-to-speech provider adapters.

    This adapter pattern allows the system to support multiple TTS providers
    (Azure TTS, Google TTS, ElevenLabs, etc.) through a unified interface.
    Each provider implementation handles the specifics of parameter conversion,
    API calls, and response parsing.

    Requirements:
    - 6.1: Unified adapter interface for all providers
    - 6.2: Parameter conversion and response normalization
    """

    def __init__(self, provider_name: str):
        """
        Initialize the TTS provider adapter.

        Args:
            provider_name: Name of the provider (e.g., 'azure', 'google', 'elevenlabs')
        """
        self.provider_name = provider_name

    @abstractmethod
    def synthesize_speech(
        self,
        text: str,
        voice: str,
        language: str = "zh-CN",
        speed: float = 1.0,
        shot_id: Optional[UUID] = None,
        **kwargs,
    ) -> TTSResult:
        """
        Synthesize speech from text.

        This method must be implemented by each provider adapter to handle
        the specifics of that provider's API.

        Args:
            text: Text to synthesize
            voice: Voice name or ID (provider-specific)
            language: BCP-47 language code (e.g., 'zh-CN', 'en-US')
            speed: Speech speed multiplier (1.0 = normal)
            shot_id: Optional shot ID for tracking
            **kwargs: Provider-specific additional parameters

        Returns:
            TTSResult: Result containing audio data or error

        Raises:
            TTSProviderError: If the provider operation fails
        """
        pass

    def validate_parameters(self, text: str, speed: float) -> None:
        """
        Validate common parameters before making provider call.

        Args:
            text: The text to validate
            speed: Speech speed to validate

        Raises:
            ValueError: If parameters are invalid
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if speed <= 0 or speed > 4.0:
            raise ValueError(f"Invalid speed: {speed} (must be between 0 and 4.0)")
