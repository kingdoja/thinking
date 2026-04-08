"""
Mock Image Provider for testing and development.

This provider generates placeholder images without calling external APIs,
useful for testing the media pipeline without incurring costs or requiring
external service availability.
"""
from typing import Optional
from uuid import UUID
import io
from PIL import Image, ImageDraw, ImageFont

from .image_provider import (
    ImageProviderAdapter,
    ImageGenerationResult,
)


class MockImageProvider(ImageProviderAdapter):
    """
    Mock image provider that generates simple placeholder images.
    
    Useful for:
    - Testing without external API dependencies
    - Development without API costs
    - CI/CD pipelines
    """
    
    def __init__(
        self,
        should_fail: bool = False,
        failure_rate: float = 0.0,
    ):
        """
        Initialize mock provider.
        
        Args:
            should_fail: If True, always fail
            failure_rate: Probability of failure (0.0 to 1.0)
        """
        super().__init__(provider_name="mock")
        self.should_fail = should_fail
        self.failure_rate = failure_rate
        self._call_count = 0
    
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
        Generate a mock placeholder image.
        
        Args:
            prompt: Prompt text (will be displayed on image)
            negative_prompt: Ignored in mock
            width: Image width
            height: Image height
            style: Ignored in mock
            shot_id: Shot ID for tracking
            **kwargs: Ignored in mock
            
        Returns:
            ImageGenerationResult with placeholder image
        """
        self._call_count += 1
        
        # Validate parameters and return error result if invalid
        try:
            self.validate_parameters(prompt, width, height)
        except ValueError as e:
            return ImageGenerationResult(
                success=False,
                error=str(e),
                shot_id=shot_id,
            )
        
        # Simulate failure if configured
        if self.should_fail:
            return ImageGenerationResult(
                success=False,
                error="Mock provider configured to fail",
                shot_id=shot_id,
            )
        
        # Simulate random failures
        import random
        if random.random() < self.failure_rate:
            return ImageGenerationResult(
                success=False,
                error=f"Mock random failure (call #{self._call_count})",
                shot_id=shot_id,
            )
        
        # Generate placeholder image
        try:
            image_data = self._generate_placeholder(
                width=width,
                height=height,
                text=prompt[:100],  # Truncate long prompts
            )
            
            return ImageGenerationResult(
                success=True,
                image_data=image_data,
                width=width,
                height=height,
                format="png",
                shot_id=shot_id,
                provider_metadata={
                    "mock": True,
                    "call_count": self._call_count,
                },
                generation_time_ms=100,  # Simulate fast generation
            )
        except Exception as e:
            return ImageGenerationResult(
                success=False,
                error=f"Failed to generate placeholder: {str(e)}",
                shot_id=shot_id,
            )
    
    def _generate_placeholder(
        self,
        width: int,
        height: int,
        text: str,
    ) -> bytes:
        """
        Generate a simple placeholder image with text.
        
        Args:
            width: Image width
            height: Image height
            text: Text to display on image
            
        Returns:
            PNG image data as bytes
        """
        # Create image with gradient background
        image = Image.new("RGB", (width, height), color=(100, 100, 150))
        draw = ImageDraw.Draw(image)
        
        # Draw border
        border_width = 10
        draw.rectangle(
            [border_width, border_width, width - border_width, height - border_width],
            outline=(200, 200, 200),
            width=border_width,
        )
        
        # Draw text (prompt)
        try:
            # Try to use a default font, fall back to basic if not available
            font = ImageFont.load_default()
        except:
            font = None
        
        # Wrap text to fit image
        max_width = width - 100
        lines = self._wrap_text(text, max_width, draw, font)
        
        # Calculate text position (centered)
        text_height = len(lines) * 20
        y = (height - text_height) // 2
        
        for line in lines:
            # Get text bounding box for centering
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            
            draw.text((x, y), line, fill=(255, 255, 255), font=font)
            y += 20
        
        # Add "MOCK" watermark
        draw.text(
            (width - 100, height - 40),
            "MOCK",
            fill=(255, 100, 100),
            font=font,
        )
        
        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    
    def _wrap_text(
        self,
        text: str,
        max_width: int,
        draw: ImageDraw.ImageDraw,
        font,
    ) -> list:
        """
        Wrap text to fit within max width.
        
        Args:
            text: Text to wrap
            max_width: Maximum width in pixels
            draw: ImageDraw instance
            font: Font to use
            
        Returns:
            List of text lines
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines[:10]  # Limit to 10 lines
