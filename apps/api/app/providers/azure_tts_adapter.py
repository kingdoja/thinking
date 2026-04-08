"""
Azure Cognitive Services TTS Provider Adapter.

Integrates with Azure Text-to-Speech (Speech SDK / REST API) to synthesize
speech from text using the unified TTSProviderAdapter interface.

Requirements:
- 6.1: Unified interface implementation
- 6.2: Parameter conversion to Azure SSML format
- 6.3: Audio normalization to MP3
- 6.4: Error handling and retry logic
"""
import io
import time
import logging
from typing import Optional, Dict, Any
from uuid import UUID

import requests

from .tts_provider import TTSProviderAdapter, TTSResult, TTSProviderError

logger = logging.getLogger(__name__)

# Azure TTS REST endpoint template
_AZURE_TTS_URL = (
    "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
)

# SSML template for Azure TTS
_SSML_TEMPLATE = """<speak version='1.0' xml:lang='{language}'>
  <voice xml:lang='{language}' xml:gender='{gender}' name='{voice}'>
    <prosody rate='{rate}'>
      {text}
    </prosody>
  </voice>
</speak>"""


class AzureTTSAdapter(TTSProviderAdapter):
    """
    Azure Cognitive Services Text-to-Speech adapter.

    Uses the Azure TTS REST API with SSML to synthesize speech and returns
    audio normalized to MP3 format.

    Requirements:
    - 6.1: Unified interface implementation
    - 6.2: Parameter conversion to Azure SSML format
    - 6.3: Audio normalization to MP3
    - 6.4: Error handling and retry logic
    """

    def __init__(
        self,
        subscription_key: str,
        region: str,
        default_voice: str = "zh-CN-XiaoxiaoNeural",
        output_format: str = "audio-16khz-128kbitrate-mono-mp3",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Azure TTS adapter.

        Args:
            subscription_key: Azure Speech Services subscription key
            region: Azure region (e.g., 'eastus', 'westeurope')
            default_voice: Default voice name to use when none specified
            output_format: Azure output format string (determines codec/bitrate)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        super().__init__(provider_name="azure_tts")
        self.subscription_key = subscription_key
        self.region = region
        self.default_voice = default_voice
        self.output_format = output_format
        self.timeout = timeout
        self.max_retries = max_retries
        self._endpoint = _AZURE_TTS_URL.format(region=region)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

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
        Synthesize speech using Azure TTS.

        Args:
            text: Text to synthesize
            voice: Azure voice name (e.g., 'zh-CN-XiaoxiaoNeural').
                   Falls back to default_voice when None.
            language: BCP-47 language code
            speed: Speech speed multiplier (0.5–2.0 recommended for Azure)
            shot_id: Optional shot ID for tracking
            **kwargs: Additional Azure-specific parameters:
                - gender (str): 'Female' or 'Male' (default 'Female')

        Returns:
            TTSResult with MP3 audio data or error details
        """
        # Validate common parameters
        try:
            self.validate_parameters(text, speed)
        except ValueError as exc:
            return TTSResult(
                success=False,
                error=str(exc),
                shot_id=shot_id,
            )

        resolved_voice = voice or self.default_voice
        gender = kwargs.get("gender", "Female")

        # Build SSML payload
        ssml = self._build_ssml(
            text=text,
            voice=resolved_voice,
            language=language,
            speed=speed,
            gender=gender,
        )

        start_time = time.time()
        result = self._call_api_with_retry(ssml, shot_id, len(text))
        result.synthesis_time_ms = int((time.time() - start_time) * 1000)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_ssml(
        self,
        text: str,
        voice: str,
        language: str,
        speed: float,
        gender: str,
    ) -> str:
        """
        Build SSML markup for Azure TTS.

        Azure prosody rate accepts values like '+10%', '-10%', or a float
        relative to 1.0 expressed as a percentage string.

        Args:
            text: Plain text to wrap in SSML
            voice: Azure voice name
            language: BCP-47 language code
            speed: Speed multiplier (1.0 = normal)
            gender: 'Female' or 'Male'

        Returns:
            SSML string
        """
        # Convert speed multiplier to Azure percentage string
        rate_pct = int((speed - 1.0) * 100)
        if rate_pct >= 0:
            rate_str = f"+{rate_pct}%"
        else:
            rate_str = f"{rate_pct}%"

        # Escape XML special characters in text
        safe_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        return _SSML_TEMPLATE.format(
            language=language,
            gender=gender,
            voice=voice,
            rate=rate_str,
            text=safe_text,
        )

    def _call_api_with_retry(
        self,
        ssml: str,
        shot_id: Optional[UUID],
        character_count: int,
    ) -> TTSResult:
        """
        Call Azure TTS REST API with exponential backoff retry.

        Args:
            ssml: SSML payload
            shot_id: Shot ID for tracking
            character_count: Number of characters (for cost tracking)

        Returns:
            TTSResult
        """
        last_error: Optional[TTSProviderError] = None

        for attempt in range(self.max_retries):
            try:
                return self._call_api(ssml, shot_id, character_count)
            except TTSProviderError as exc:
                last_error = exc

                if not exc.is_retryable:
                    logger.error(f"Permanent Azure TTS error: {exc}")
                    break

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Azure TTS call failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait_time}s: {exc}"
                    )
                    time.sleep(wait_time)

        return TTSResult(
            success=False,
            error=str(last_error) if last_error else "Unknown error",
            shot_id=shot_id,
            request_id=last_error.request_id if last_error else None,
            character_count=character_count,
        )

    def _call_api(
        self,
        ssml: str,
        shot_id: Optional[UUID],
        character_count: int,
    ) -> TTSResult:
        """
        Make a single REST call to Azure TTS.

        Args:
            ssml: SSML payload
            shot_id: Shot ID for tracking
            character_count: Number of characters synthesized

        Returns:
            TTSResult with MP3 audio data

        Raises:
            TTSProviderError: On any API failure
        """
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": self.output_format,
            "User-Agent": "thinking-api/1.0",
        }

        try:
            response = requests.post(
                self._endpoint,
                data=ssml.encode("utf-8"),
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            raise TTSProviderError(
                message="Request timeout",
                provider_name=self.provider_name,
                is_retryable=True,
            )
        except requests.exceptions.ConnectionError as exc:
            raise TTSProviderError(
                message=f"Connection error: {exc}",
                provider_name=self.provider_name,
                is_retryable=True,
            )
        except requests.exceptions.RequestException as exc:
            raise TTSProviderError(
                message=f"Request failed: {exc}",
                provider_name=self.provider_name,
                is_retryable=False,
            )

        # Extract request-id header for tracking
        request_id = response.headers.get("X-RequestId")

        if response.status_code == 429:
            raise TTSProviderError(
                message="Rate limit exceeded",
                provider_name=self.provider_name,
                request_id=request_id,
                is_retryable=True,
                status_code=429,
            )
        elif response.status_code >= 500:
            raise TTSProviderError(
                message=f"Server error: {response.text[:200]}",
                provider_name=self.provider_name,
                request_id=request_id,
                is_retryable=True,
                status_code=response.status_code,
            )
        elif response.status_code >= 400:
            raise TTSProviderError(
                message=f"Client error ({response.status_code}): {response.text[:200]}",
                provider_name=self.provider_name,
                request_id=request_id,
                is_retryable=False,
                status_code=response.status_code,
            )

        # Success — parse audio response
        return self._parse_response(
            audio_bytes=response.content,
            shot_id=shot_id,
            request_id=request_id,
            character_count=character_count,
        )

    def _parse_response(
        self,
        audio_bytes: bytes,
        shot_id: Optional[UUID],
        request_id: Optional[str],
        character_count: int,
    ) -> TTSResult:
        """
        Parse Azure TTS audio response.

        Azure returns raw audio bytes in the requested output format.
        We normalize to MP3 and estimate duration from byte size.

        Args:
            audio_bytes: Raw audio bytes from Azure
            shot_id: Shot ID for tracking
            request_id: Azure request ID
            character_count: Number of characters synthesized

        Returns:
            TTSResult with audio data
        """
        if not audio_bytes:
            return TTSResult(
                success=False,
                error="Empty audio response from Azure TTS",
                shot_id=shot_id,
                request_id=request_id,
                character_count=character_count,
            )

        # Determine format from output_format string
        audio_format = "mp3" if "mp3" in self.output_format else "wav"

        # Estimate duration from MP3 bitrate (128 kbps default)
        duration_ms: Optional[int] = None
        if audio_format == "mp3":
            # Extract bitrate from format string, e.g. "audio-16khz-128kbitrate-mono-mp3"
            bitrate_kbps = self._extract_bitrate_kbps()
            if bitrate_kbps:
                duration_ms = int((len(audio_bytes) * 8) / bitrate_kbps)

        # Determine sample rate from format string
        sample_rate = self._extract_sample_rate_hz()

        return TTSResult(
            success=True,
            audio_data=audio_bytes,
            audio_format=audio_format,
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            channels=1,  # Azure mono output
            shot_id=shot_id,
            request_id=request_id,
            character_count=character_count,
            provider_metadata={
                "provider": "azure_tts",
                "region": self.region,
                "output_format": self.output_format,
            },
        )

    def _extract_bitrate_kbps(self) -> Optional[int]:
        """Extract bitrate in kbps from the output_format string."""
        import re
        match = re.search(r"(\d+)kbitrate", self.output_format)
        return int(match.group(1)) if match else None

    def _extract_sample_rate_hz(self) -> Optional[int]:
        """Extract sample rate in Hz from the output_format string."""
        import re
        match = re.search(r"(\d+)khz", self.output_format)
        return int(match.group(1)) * 1000 if match else None
