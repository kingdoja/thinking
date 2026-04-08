"""
Unit tests for Image Provider adapters.

Tests the base adapter interface, mock provider, and factory pattern.
"""
import pytest
from uuid import uuid4

from app.providers import (
    ImageProviderAdapter,
    ImageGenerationResult,
    ProviderError,
    MockImageProvider,
    ImageProviderFactory,
)


class TestImageProviderAdapter:
    """Test the base ImageProviderAdapter interface."""
    
    def test_validate_parameters_empty_prompt(self):
        """Test that empty prompt raises ValueError."""
        provider = MockImageProvider()
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            provider.validate_parameters("", 1080, 1920)
    
    def test_validate_parameters_invalid_dimensions(self):
        """Test that invalid dimensions raise ValueError."""
        provider = MockImageProvider()
        
        with pytest.raises(ValueError, match="Invalid dimensions"):
            provider.validate_parameters("test prompt", 0, 1920)
        
        with pytest.raises(ValueError, match="Invalid dimensions"):
            provider.validate_parameters("test prompt", 1080, -100)
    
    def test_validate_parameters_too_large(self):
        """Test that dimensions over 4096 raise ValueError."""
        provider = MockImageProvider()
        
        with pytest.raises(ValueError, match="Dimensions too large"):
            provider.validate_parameters("test prompt", 5000, 1920)


class TestMockImageProvider:
    """Test the MockImageProvider implementation."""
    
    def test_generate_image_success(self):
        """Test successful image generation."""
        provider = MockImageProvider()
        
        result = provider.generate_image(
            prompt="A beautiful landscape",
            width=512,
            height=512,
        )
        
        assert result.success is True
        assert result.image_data is not None
        assert len(result.image_data) > 0
        assert result.width == 512
        assert result.height == 512
        assert result.format == "png"
        assert result.provider_metadata["mock"] is True
    
    def test_generate_image_with_shot_id(self):
        """Test image generation with shot ID tracking."""
        provider = MockImageProvider()
        shot_id = uuid4()
        
        result = provider.generate_image(
            prompt="Test prompt",
            shot_id=shot_id,
        )
        
        assert result.success is True
        assert result.shot_id == shot_id
    
    def test_generate_image_configured_failure(self):
        """Test that provider fails when configured to fail."""
        provider = MockImageProvider(should_fail=True)
        
        result = provider.generate_image(
            prompt="Test prompt",
        )
        
        assert result.success is False
        assert result.error is not None
        assert "configured to fail" in result.error
    
    def test_generate_image_random_failure(self):
        """Test random failure rate."""
        provider = MockImageProvider(failure_rate=1.0)  # Always fail
        
        result = provider.generate_image(
            prompt="Test prompt",
        )
        
        assert result.success is False
        assert result.error is not None
        assert "random failure" in result.error
    
    def test_generate_image_invalid_prompt(self):
        """Test that invalid prompt is caught."""
        provider = MockImageProvider()
        
        result = provider.generate_image(
            prompt="",
            width=512,
            height=512,
        )
        
        assert result.success is False
        assert result.error is not None


class TestImageProviderFactory:
    """Test the ImageProviderFactory."""
    
    def test_create_mock_provider(self):
        """Test creating mock provider."""
        provider = ImageProviderFactory.create_provider(provider_type="mock")
        
        assert isinstance(provider, MockImageProvider)
        assert provider.provider_name == "mock"
    
    def test_create_stable_diffusion_provider(self):
        """Test creating Stable Diffusion provider."""
        from app.providers.stable_diffusion_adapter import StableDiffusionAdapter
        
        provider = ImageProviderFactory.create_provider(
            provider_type="stable_diffusion",
            api_url="http://test:7860",
        )
        
        assert isinstance(provider, StableDiffusionAdapter)
        assert provider.provider_name == "stable_diffusion"
    
    def test_create_unsupported_provider(self):
        """Test that unsupported provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported image provider"):
            ImageProviderFactory.create_provider(provider_type="unsupported")
    
    def test_get_provider_singleton(self):
        """Test that get_provider returns singleton."""
        ImageProviderFactory.reset_provider()
        
        provider1 = ImageProviderFactory.get_provider()
        provider2 = ImageProviderFactory.get_provider()
        
        assert provider1 is provider2
    
    def test_reset_provider(self):
        """Test that reset_provider clears singleton."""
        ImageProviderFactory.reset_provider()
        provider1 = ImageProviderFactory.get_provider()
        
        ImageProviderFactory.reset_provider()
        provider2 = ImageProviderFactory.get_provider()
        
        assert provider1 is not provider2


class TestProviderError:
    """Test the ProviderError exception."""
    
    def test_provider_error_basic(self):
        """Test basic ProviderError creation."""
        error = ProviderError(
            message="Test error",
            provider_name="test_provider",
        )
        
        assert error.message == "Test error"
        assert error.provider_name == "test_provider"
        assert error.is_retryable is False
        assert error.request_id is None
    
    def test_provider_error_with_details(self):
        """Test ProviderError with all details."""
        error = ProviderError(
            message="Rate limit exceeded",
            provider_name="test_provider",
            request_id="req_123",
            is_retryable=True,
            status_code=429,
        )
        
        assert error.message == "Rate limit exceeded"
        assert error.request_id == "req_123"
        assert error.is_retryable is True
        assert error.status_code == 429
    
    def test_provider_error_string_representation(self):
        """Test ProviderError string formatting."""
        error = ProviderError(
            message="Test error",
            provider_name="test_provider",
            request_id="req_123",
            status_code=500,
        )
        
        error_str = str(error)
        assert "test_provider" in error_str
        assert "Test error" in error_str
        assert "req_123" in error_str
        assert "500" in error_str


class TestImageGenerationResult:
    """Test the ImageGenerationResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        result = ImageGenerationResult(
            success=True,
            image_data=b"fake_image_data",
            width=1080,
            height=1920,
            format="png",
        )
        
        assert result.success is True
        assert result.image_data == b"fake_image_data"
        assert result.width == 1080
        assert result.height == 1920
        assert result.format == "png"
    
    def test_failure_result(self):
        """Test creating a failure result."""
        result = ImageGenerationResult(
            success=False,
            error="Generation failed",
        )
        
        assert result.success is False
        assert result.error == "Generation failed"
        assert result.image_data is None
