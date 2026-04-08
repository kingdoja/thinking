# Image Provider Adapter

## Overview

The Image Provider Adapter is a flexible abstraction layer that allows the system to integrate with multiple image generation services (Stable Diffusion, DALL-E, Midjourney, etc.) through a unified interface.

## Architecture

```
┌─────────────────────────────────────┐
│   Image Render Stage                │
│   (Business Logic)                  │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│   ImageProviderAdapter              │
│   (Abstract Interface)              │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┬──────────┐
       ↓                ↓          ↓
┌──────────────┐ ┌──────────┐ ┌────────┐
│ Stable       │ │ Mock     │ │ DALL-E │
│ Diffusion    │ │ Provider │ │ (TBD)  │
└──────────────┘ └──────────┘ └────────┘
```

## Components

### 1. ImageProviderAdapter (Base Class)

Abstract base class defining the interface all providers must implement.

**Key Methods:**
- `generate_image()`: Generate an image from a prompt
- `validate_parameters()`: Validate input parameters

### 2. ImageGenerationResult (Data Class)

Standardized result format returned by all providers.

**Fields:**
- `success`: Whether generation succeeded
- `image_data`: Binary image data (PNG/JPEG bytes)
- `image_url`: Optional URL to the image
- `width`, `height`: Image dimensions
- `format`: Image format (png, jpeg, etc.)
- `shot_id`: Associated shot ID for tracking
- `provider_metadata`: Provider-specific metadata
- `error`: Error message if failed
- `request_id`: Provider's request ID
- `generation_time_ms`: Generation time

### 3. ProviderError (Exception)

Exception raised when provider operations fail.

**Attributes:**
- `message`: Error description
- `provider_name`: Which provider raised the error
- `request_id`: Provider's request ID
- `is_retryable`: Whether the error is temporary
- `status_code`: HTTP status code if applicable

### 4. StableDiffusionAdapter

Implementation for Stable Diffusion API (Automatic1111 WebUI format).

**Features:**
- Parameter conversion to SD format
- Exponential backoff retry logic
- Rate limit handling
- Base64 image decoding
- Metadata extraction

**Configuration:**
- `api_url`: SD API endpoint
- `api_key`: Optional authentication
- `model`: Model/checkpoint to use
- `timeout`: Request timeout
- `max_retries`: Maximum retry attempts

### 5. MockImageProvider

Mock provider for testing and development.

**Features:**
- Generates placeholder images with text
- No external API dependencies
- Configurable failure modes
- Fast generation for testing

**Use Cases:**
- Unit testing
- CI/CD pipelines
- Development without API costs
- Integration testing

### 6. ImageProviderFactory

Factory for creating provider instances based on configuration.

**Methods:**
- `create_provider()`: Create a new provider instance
- `get_provider()`: Get or create singleton instance
- `reset_provider()`: Reset singleton (for testing)

## Configuration

Add to `.env`:

```env
# Image Provider Configuration
IMAGE_PROVIDER=stable_diffusion  # Options: stable_diffusion, mock
IMAGE_PROVIDER_API_URL=http://localhost:7860
IMAGE_PROVIDER_API_KEY=
IMAGE_PROVIDER_MODEL=sd_xl_base_1.0
IMAGE_PROVIDER_TIMEOUT=120
IMAGE_PROVIDER_MAX_RETRIES=3
```

## Usage

### Basic Usage

```python
from app.providers import ImageProviderFactory

# Get configured provider
provider = ImageProviderFactory.get_provider()

# Generate image
result = provider.generate_image(
    prompt="A beautiful landscape with mountains",
    negative_prompt="low quality, blurry",
    width=1080,
    height=1920,
    style="cinematic, detailed",
)

if result.success:
    # Save image
    with open("output.png", "wb") as f:
        f.write(result.image_data)
else:
    print(f"Generation failed: {result.error}")
```

### Using Specific Provider

```python
from app.providers import ImageProviderFactory

# Create specific provider
provider = ImageProviderFactory.create_provider(
    provider_type="stable_diffusion",
    api_url="http://custom-sd-server:7860",
)

result = provider.generate_image(
    prompt="Test prompt",
    width=512,
    height=512,
)
```

### Mock Provider for Testing

```python
from app.providers import MockImageProvider

# Create mock provider
provider = MockImageProvider()

# Generate placeholder
result = provider.generate_image(
    prompt="Test image",
    width=512,
    height=512,
)

assert result.success
assert result.image_data is not None
```

## Adding New Providers

To add support for a new image generation service:

1. Create a new adapter class inheriting from `ImageProviderAdapter`
2. Implement the `generate_image()` method
3. Handle provider-specific parameter conversion
4. Parse provider-specific responses
5. Add to factory in `image_provider_factory.py`

Example:

```python
from app.providers.image_provider import (
    ImageProviderAdapter,
    ImageGenerationResult,
    ProviderError,
)

class DALLEAdapter(ImageProviderAdapter):
    def __init__(self, api_key: str):
        super().__init__(provider_name="dalle")
        self.api_key = api_key
    
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
        # Validate
        self.validate_parameters(prompt, width, height)
        
        # Convert parameters to DALL-E format
        dalle_params = self._convert_parameters(...)
        
        # Call DALL-E API
        response = self._call_dalle_api(dalle_params)
        
        # Parse response
        return self._parse_response(response, shot_id)
```

## Error Handling

The adapter implements robust error handling:

### Retryable Errors
- Network timeouts
- Rate limits (429)
- Server errors (5xx)

These errors trigger exponential backoff retry.

### Non-Retryable Errors
- Invalid parameters (400)
- Authentication errors (401, 403)
- Not found (404)

These errors fail immediately without retry.

### Example

```python
try:
    result = provider.generate_image(prompt="test")
    if not result.success:
        if result.error:
            logger.error(f"Generation failed: {result.error}")
except ProviderError as e:
    if e.is_retryable:
        logger.warning(f"Temporary error: {e}")
    else:
        logger.error(f"Permanent error: {e}")
```

## Testing

Run the test suite:

```bash
cd apps/api
python -m pytest tests/unit/test_image_provider.py -v
```

## Performance Considerations

- **Timeouts**: Default 120s, adjust based on provider
- **Retries**: Default 3 attempts with exponential backoff
- **Concurrency**: Use async/await for parallel generation
- **Caching**: Consider caching identical prompts

## Cost Monitoring

Track provider costs by:
1. Recording each API call
2. Estimating cost based on provider pricing
3. Storing in `StageTask.metrics_jsonb`

## Security

- Store API keys in environment variables
- Use HTTPS for API calls
- Validate all inputs before sending to provider
- Sanitize error messages before logging

## Future Enhancements

- [ ] Support for DALL-E 3
- [ ] Support for Midjourney
- [ ] Support for Runway
- [ ] Image-to-image generation
- [ ] ControlNet support
- [ ] LoRA model support
- [ ] Prompt optimization
- [ ] Quality scoring
- [ ] Automatic retry with prompt variations
