"""
Stable Diffusion Provider Adapter implementation.

This adapter integrates with Stable Diffusion API (or compatible APIs like
Automatic1111, ComfyUI, or cloud providers offering SD models).
"""
import time
import requests
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from .image_provider import (
    ImageProviderAdapter,
    ImageGenerationResult,
    ProviderError,
)

logger = logging.getLogger(__name__)


class StableDiffusionAdapter(ImageProviderAdapter):
    """
    Stable Diffusion provider adapter.
    
    Supports Stable Diffusion API endpoints (Automatic1111 WebUI API format).
    
    Requirements:
    - 3.1: Unified interface implementation
    - 3.2: Parameter conversion to SD format
    - 3.3: Response parsing from SD format
    - 3.4: Error handling and retry logic
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        model: str = "sd_xl_base_1.0",
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize Stable Diffusion adapter.
        
        Args:
            api_url: Base URL of the SD API endpoint
            api_key: Optional API key for authentication
            model: Model name/checkpoint to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        super().__init__(provider_name="stable_diffusion")
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
    
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
        Generate image using Stable Diffusion.
        
        Args:
            prompt: Positive prompt
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            style: Style keywords to append to prompt
            shot_id: Shot ID for tracking
            **kwargs: Additional SD parameters (steps, cfg_scale, sampler, etc.)
            
        Returns:
            ImageGenerationResult with generated image or error
        """
        # Validate parameters
        self.validate_parameters(prompt, width, height)
        
        # Convert parameters to SD format
        sd_params = self._convert_parameters(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            style=style,
            **kwargs
        )
        
        # Make API call with retry logic
        start_time = time.time()
        result = self._call_api_with_retry(sd_params, shot_id)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        # Add generation time to result
        result.generation_time_ms = generation_time_ms
        
        return result
    
    def _convert_parameters(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int,
        style: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convert internal parameters to Stable Diffusion API format.
        
        Args:
            prompt: Positive prompt
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            style: Style keywords
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of SD API parameters
        """
        # Append style to prompt if provided
        full_prompt = prompt
        if style:
            full_prompt = f"{prompt}, {style}"
        
        # Default negative prompt if not provided
        if not negative_prompt:
            negative_prompt = (
                "low quality, blurry, distorted, deformed, "
                "ugly, bad anatomy, watermark, text"
            )
        
        # Build SD API parameters
        sd_params = {
            "prompt": full_prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": kwargs.get("steps", 30),
            "cfg_scale": kwargs.get("cfg_scale", 7.0),
            "sampler_name": kwargs.get("sampler", "DPM++ 2M Karras"),
            "seed": kwargs.get("seed", -1),  # -1 for random
            "batch_size": 1,
            "n_iter": 1,
        }
        
        # Add model override if specified
        if "model" in kwargs:
            sd_params["override_settings"] = {
                "sd_model_checkpoint": kwargs["model"]
            }
        elif self.model:
            sd_params["override_settings"] = {
                "sd_model_checkpoint": self.model
            }
        
        return sd_params
    
    def _call_api_with_retry(
        self,
        params: Dict[str, Any],
        shot_id: Optional[UUID]
    ) -> ImageGenerationResult:
        """
        Call SD API with exponential backoff retry logic.
        
        Args:
            params: SD API parameters
            shot_id: Shot ID for tracking
            
        Returns:
            ImageGenerationResult
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return self._call_api(params, shot_id)
            except ProviderError as e:
                last_error = e
                
                # Don't retry on permanent errors (4xx except 429)
                if not e.is_retryable:
                    logger.error(f"Permanent error from SD API: {e}")
                    break
                
                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"SD API call failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
        
        # All retries failed
        return ImageGenerationResult(
            success=False,
            error=str(last_error) if last_error else "Unknown error",
            shot_id=shot_id,
            request_id=last_error.request_id if last_error else None,
        )
    
    def _call_api(
        self,
        params: Dict[str, Any],
        shot_id: Optional[UUID]
    ) -> ImageGenerationResult:
        """
        Make actual API call to Stable Diffusion.
        
        Args:
            params: SD API parameters
            shot_id: Shot ID for tracking
            
        Returns:
            ImageGenerationResult
            
        Raises:
            ProviderError: If API call fails
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        endpoint = f"{self.api_url}/sdapi/v1/txt2img"
        
        try:
            response = requests.post(
                endpoint,
                json=params,
                headers=headers,
                timeout=self.timeout,
            )
            
            # Handle HTTP errors
            if response.status_code == 429:
                # Rate limit - retryable
                raise ProviderError(
                    message="Rate limit exceeded",
                    provider_name=self.provider_name,
                    is_retryable=True,
                    status_code=429,
                )
            elif response.status_code >= 500:
                # Server error - retryable
                raise ProviderError(
                    message=f"Server error: {response.text}",
                    provider_name=self.provider_name,
                    is_retryable=True,
                    status_code=response.status_code,
                )
            elif response.status_code >= 400:
                # Client error - not retryable
                raise ProviderError(
                    message=f"Client error: {response.text}",
                    provider_name=self.provider_name,
                    is_retryable=False,
                    status_code=response.status_code,
                )
            
            response.raise_for_status()
            
            # Parse response
            return self._parse_response(response.json(), shot_id)
            
        except requests.exceptions.Timeout:
            raise ProviderError(
                message="Request timeout",
                provider_name=self.provider_name,
                is_retryable=True,
            )
        except requests.exceptions.ConnectionError as e:
            raise ProviderError(
                message=f"Connection error: {str(e)}",
                provider_name=self.provider_name,
                is_retryable=True,
            )
        except requests.exceptions.RequestException as e:
            raise ProviderError(
                message=f"Request failed: {str(e)}",
                provider_name=self.provider_name,
                is_retryable=False,
            )
    
    def _parse_response(
        self,
        response_data: Dict[str, Any],
        shot_id: Optional[UUID]
    ) -> ImageGenerationResult:
        """
        Parse Stable Diffusion API response.
        
        Args:
            response_data: JSON response from SD API
            shot_id: Shot ID for tracking
            
        Returns:
            ImageGenerationResult
        """
        try:
            # SD API returns base64 encoded images
            import base64
            
            images = response_data.get("images", [])
            if not images:
                return ImageGenerationResult(
                    success=False,
                    error="No images in response",
                    shot_id=shot_id,
                )
            
            # Get first image
            image_b64 = images[0]
            image_data = base64.b64decode(image_b64)
            
            # Extract metadata
            info = response_data.get("info", {})
            parameters = response_data.get("parameters", {})
            
            # Determine format (SD usually returns PNG)
            format_type = "png"
            
            # Build provider metadata
            provider_metadata = {
                "model": self.model,
                "seed": info.get("seed"),
                "steps": parameters.get("steps"),
                "cfg_scale": parameters.get("cfg_scale"),
                "sampler": parameters.get("sampler_name"),
            }
            
            return ImageGenerationResult(
                success=True,
                image_data=image_data,
                width=parameters.get("width"),
                height=parameters.get("height"),
                format=format_type,
                shot_id=shot_id,
                provider_metadata=provider_metadata,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse SD response: {e}")
            return ImageGenerationResult(
                success=False,
                error=f"Failed to parse response: {str(e)}",
                shot_id=shot_id,
            )
