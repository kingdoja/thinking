"""
Mock TTS Provider for testing and development.

Generates minimal silent WAV audio without calling external APIs,
useful for testing the media pipeline without incurring costs.
"""
import struct
import time
from typing import Optional
from uuid import UUID

from .tts_provider import TTSProviderAdapter, TTSResult


def _make_silent_wav(duration_ms: int = 1000, sample_rate: int = 16000) -> bytes:
    """
    Build a minimal silent PCM WAV file in memory.

    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz

    Returns:
        WAV file bytes
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    pcm_data = b"\x00\x00" * num_samples  # 16-bit silence, mono

    # WAV header
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,           # chunk size
        1,            # PCM format
        1,            # mono
        sample_rate,
        sample_rate * 2,  # byte rate
        2,            # block align
        16,           # bits per sample
        b"data",
        data_size,
    )
    return header + pcm_data


class MockTTSProvider(TTSProviderAdapter):
    """
    Mock TTS provider that returns silent WAV audio.

    Useful for:
    - Testing without external API dependencies
    - Development without API costs
    - CI/CD pipelines
    """

    def __init__(
        self,
        should_fail: bool = False,
        failure_rate: float = 0.0,
        words_per_minute: int = 150,
    ):
        """
        Initialize mock TTS provider.

        Args:
            should_fail: If True, always return a failure result
            failure_rate: Probability of failure (0.0 to 1.0)
            words_per_minute: Used to estimate audio duration from text
        """
        super().__init__(provider_name="mock_tts")
        self.should_fail = should_fail
        self.failure_rate = failure_rate
        self.words_per_minute = words_per_minute
        self._call_count = 0

    def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "zh-CN",
        speed: float = 1.0,
        shot_id: Optional[UUID] = None,
        **kwargs,
    ) -> TTSResult:
        """
        Return a silent WAV clip whose duration matches the text length.

        Args:
            text: Text to synthesize
            voice: Ignored in mock
            language: Ignored in mock
            speed: Affects estimated duration
            shot_id: Shot ID for tracking
            **kwargs: Ignored in mock

        Returns:
            TTSResult with silent WAV audio
        """
        self._call_count += 1

        try:
            self.validate_parameters(text, speed)
        except ValueError as exc:
            return TTSResult(success=False, error=str(exc), shot_id=shot_id)

        if self.should_fail:
            return TTSResult(
                success=False,
                error="Mock TTS provider configured to fail",
                shot_id=shot_id,
            )

        import random
        if random.random() < self.failure_rate:
            return TTSResult(
                success=False,
                error=f"Mock random failure (call #{self._call_count})",
                shot_id=shot_id,
            )

        # Estimate duration from word count and speed
        word_count = len(text.split())
        duration_ms = max(500, int(word_count / self.words_per_minute * 60_000 / speed))

        audio_data = _make_silent_wav(duration_ms=duration_ms)

        return TTSResult(
            success=True,
            audio_data=audio_data,
            audio_format="wav",
            duration_ms=duration_ms,
            sample_rate=16000,
            channels=1,
            shot_id=shot_id,
            character_count=len(text),
            synthesis_time_ms=50,
            provider_metadata={
                "mock": True,
                "call_count": self._call_count,
            },
        )
