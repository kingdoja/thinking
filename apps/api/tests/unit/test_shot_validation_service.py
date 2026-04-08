"""
Unit tests for ShotValidationService

Tests Requirements: 1.1, 2.1, 3.5, 4.2
"""

import pytest
from uuid import uuid4
from datetime import datetime

from app.services.shot_validation_service import (
    ShotValidationService,
    ValidationResult,
    ValidationError,
    ValidationWarning
)
from app.db.models import ShotModel, DocumentModel


def test_validate_shot_completeness_valid(test_session):
    """Test validation of complete shot."""
    service = ShotValidationService(test_session)
    
    # Create a valid shot
    shot = ShotModel(
        id=uuid4(),
        project_id=uuid4(),
        episode_id=uuid4(),
        scene_no=1,
        shot_no=1,
        shot_code="S01_001",
        status="draft",
        duration_ms=5000,
        camera_size="medium",
        camera_angle="eye-level",
        movement_type="static",
        characters_jsonb=["Character A"],
        action_text="Test action",
        dialogue_text="Test dialogue",
        visual_constraints_jsonb={
            "render_prompt": "Test render prompt",
            "style_keywords": ["cinematic"],
            "composition": "medium",
            "character_refs": ["Character A"]
        },
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    result = service.validate_shot_completeness(shot)
    
    assert result.is_valid
    assert len(result.errors) == 0
    # May have warnings for optional fields, but should be valid


def test_validate_shot_completeness_missing_required(test_session):
    """Test validation of shot with missing required fields."""
    service = ShotValidationService(test_session)
    
    # Create shot with missing required fields
    shot = ShotModel(
        id=uuid4(),
        project_id=uuid4(),
        episode_id=uuid4(),
        scene_no=None,  # Missing
        shot_no=None,  # Missing
        shot_code="",  # Empty
        status="draft",
        duration_ms=0,  # Invalid
        characters_jsonb=[],
        visual_constraints_jsonb={},
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    result = service.validate_shot_completeness(shot)
    
    assert not result.is_valid
    assert len(result.errors) > 0
    
    # Check specific errors
    error_fields = [e.field_path for e in result.errors]
    assert 'scene_no' in error_fields
    assert 'shot_no' in error_fields
    assert 'shot_code' in error_fields
    assert 'duration_ms' in error_fields


def test_validate_visual_constraints_schema_valid(test_session):
    """Test validation of valid visual_constraints."""
    service = ShotValidationService(test_session)
    
    valid_vc = {
        "render_prompt": "A detailed render prompt with sufficient length",
        "style_keywords": ["cinematic", "dramatic"],
        "composition": "medium",
        "character_refs": ["Character A", "Character B"]
    }
    
    result = service.validate_visual_constraints_schema(valid_vc)
    
    assert result.is_valid
    assert len(result.errors) == 0


def test_validate_visual_constraints_schema_missing_fields(test_session):
    """Test validation of visual_constraints with missing fields."""
    service = ShotValidationService(test_session)
    
    invalid_vc = {
        "render_prompt": "Test"
        # Missing style_keywords, composition, character_refs
    }
    
    result = service.validate_visual_constraints_schema(invalid_vc)
    
    assert not result.is_valid
    assert len(result.errors) > 0
    
    # Check for missing field errors
    error_messages = [e.message for e in result.errors]
    assert any('style_keywords' in msg for msg in error_messages)
    assert any('composition' in msg for msg in error_messages)
    assert any('character_refs' in msg for msg in error_messages)


def test_validate_visual_constraints_schema_invalid_types(test_session):
    """Test validation of visual_constraints with invalid types."""
    service = ShotValidationService(test_session)
    
    invalid_vc = {
        "render_prompt": "",  # Empty
        "style_keywords": "not_an_array",  # Should be array
        "composition": "medium",
        "character_refs": "not_an_array"  # Should be array
    }
    
    result = service.validate_visual_constraints_schema(invalid_vc)
    
    assert not result.is_valid
    assert len(result.errors) > 0
    
    # Check for type errors
    error_messages = [e.message for e in result.errors]
    assert any('style_keywords' in msg and 'array' in msg for msg in error_messages)
    assert any('character_refs' in msg and 'array' in msg for msg in error_messages)


def test_validate_visual_constraints_schema_short_prompt(test_session):
    """Test validation warns about short render_prompt."""
    service = ShotValidationService(test_session)
    
    vc_with_short_prompt = {
        "render_prompt": "Short",  # Less than 10 characters
        "style_keywords": ["test"],
        "composition": "medium",
        "character_refs": []
    }
    
    result = service.validate_visual_constraints_schema(vc_with_short_prompt)
    
    # Should be valid but have warnings
    assert result.is_valid
    assert len(result.warnings) > 0
    
    # Check for short prompt warning
    warning_messages = [w.message for w in result.warnings]
    assert any('too short' in msg for msg in warning_messages)


def test_validate_visual_constraints_not_dict(test_session):
    """Test validation of non-dict visual_constraints."""
    service = ShotValidationService(test_session)
    
    result = service.validate_visual_constraints_schema(None)
    
    assert not result.is_valid
    assert len(result.errors) > 0
    assert any('not a valid dict' in e.message for e in result.errors)


if __name__ == "__main__":
    # Simple test runner for manual execution
    print("Run with pytest: pytest apps/api/tests/unit/test_shot_validation_service.py -v")
