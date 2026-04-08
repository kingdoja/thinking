"""
Unit tests for ImageRenderInputBuilder

Tests Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 12.1, 12.2, 12.3, 12.4, 12.5
"""

import pytest
from uuid import uuid4
from datetime import datetime

from app.services.image_render_input_builder import (
    ImageRenderInputBuilder,
    ImageRenderInput
)
from app.db.models import ShotModel, DocumentModel


def test_image_render_input_validation():
    """Test ImageRenderInput dataclass validation."""
    # Valid input
    valid_input = ImageRenderInput(
        shot_id=uuid4(),
        episode_id=uuid4(),
        prompt="A detailed render prompt",
        negative_prompt="blurry",
        style_keywords=["cinematic"],
        visual_style="anime",
        composition="medium",
        camera_size="medium",
        camera_angle="eye-level",
        character_refs=["Character A"],
        character_anchors={"Character A": "tall with blue hair"},
        aspect_ratio="9:16",
        resolution=(1080, 1920),
        scene_no=1,
        shot_no=1,
        shot_code="S01_001"
    )
    
    assert valid_input.prompt == "A detailed render prompt"
    assert valid_input.scene_no == 1
    
    # Test to_dict serialization
    data = valid_input.to_dict()
    assert isinstance(data['shot_id'], str)
    assert isinstance(data['episode_id'], str)
    assert data['resolution'] == (1080, 1920)


def test_image_render_input_validation_empty_prompt():
    """Test ImageRenderInput rejects empty prompt."""
    with pytest.raises(ValueError, match="prompt cannot be empty"):
        ImageRenderInput(
            shot_id=uuid4(),
            episode_id=uuid4(),
            prompt="",  # Empty
            negative_prompt="blurry",
            style_keywords=[],
            visual_style="anime",
            composition="medium",
            camera_size="medium",
            camera_angle="eye-level",
            character_refs=[],
            character_anchors={},
            aspect_ratio="9:16",
            resolution=(1080, 1920),
            scene_no=1,
            shot_no=1,
            shot_code="S01_001"
        )


def test_image_render_input_validation_invalid_scene_no():
    """Test ImageRenderInput rejects invalid scene_no."""
    with pytest.raises(ValueError, match="scene_no must be positive"):
        ImageRenderInput(
            shot_id=uuid4(),
            episode_id=uuid4(),
            prompt="Test prompt",
            negative_prompt="blurry",
            style_keywords=[],
            visual_style="anime",
            composition="medium",
            camera_size="medium",
            camera_angle="eye-level",
            character_refs=[],
            character_anchors={},
            aspect_ratio="9:16",
            resolution=(1080, 1920),
            scene_no=0,  # Invalid
            shot_no=1,
            shot_code="S01_001"
        )


def test_build_input_for_shot_basic(test_session):
    """Test building input for a single shot with basic data."""
    # Create test data
    project_id = uuid4()
    episode_id = uuid4()
    shot_id = uuid4()
    
    # Create shot
    shot = ShotModel(
        id=shot_id,
        project_id=project_id,
        episode_id=episode_id,
        scene_no=1,
        shot_no=1,
        shot_code="S01_001",
        status="draft",
        duration_ms=5000,
        camera_size="medium",
        camera_angle="eye-level",
        movement_type="static",
        characters_jsonb=["Alice"],
        action_text="Alice walks into the room",
        dialogue_text="Hello!",
        visual_constraints_jsonb={
            "render_prompt": "A bright room with modern furniture",
            "style_keywords": ["cinematic", "bright"],
            "composition": "medium shot",
            "character_refs": ["Alice"]
        },
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_session.add(shot)
    test_session.commit()
    
    # Create character_profile document
    char_profile = DocumentModel(
        id=uuid4(),
        project_id=project_id,
        episode_id=episode_id,
        document_type="character_profile",
        version=1,
        status="confirmed",
        content_jsonb={
            "characters": [
                {
                    "name": "Alice",
                    "role": "protagonist",
                    "goal": "find the truth",
                    "motivation": "justice",
                    "visual_anchor": "tall woman with long blue hair and green eyes"
                }
            ]
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_session.add(char_profile)
    test_session.commit()
    
    # Build input
    builder = ImageRenderInputBuilder(test_session)
    result = builder.build_input_for_shot(shot_id, episode_id)
    
    # Verify result
    assert result.shot_id == shot_id
    assert result.episode_id == episode_id
    assert "Alice" in result.prompt or "blue hair" in result.prompt
    assert result.style_keywords == ["cinematic", "bright"]
    assert result.composition == "medium shot"
    assert result.camera_size == "medium"
    assert result.camera_angle == "eye-level"
    assert result.character_refs == ["Alice"]
    assert "Alice" in result.character_anchors
    assert result.scene_no == 1
    assert result.shot_no == 1
    assert result.shot_code == "S01_001"


def test_build_input_for_shot_missing_shot(test_session):
    """Test building input for non-existent shot raises error."""
    builder = ImageRenderInputBuilder(test_session)
    
    with pytest.raises(ValueError, match="Shot .* not found"):
        builder.build_input_for_shot(uuid4(), uuid4())


def test_build_input_for_shot_empty_prompt(test_session):
    """Test building input for shot with empty prompt raises error."""
    project_id = uuid4()
    episode_id = uuid4()
    shot_id = uuid4()
    
    # Create shot with empty render_prompt
    shot = ShotModel(
        id=shot_id,
        project_id=project_id,
        episode_id=episode_id,
        scene_no=1,
        shot_no=1,
        shot_code="S01_001",
        status="draft",
        duration_ms=5000,
        visual_constraints_jsonb={
            "render_prompt": "",  # Empty
            "style_keywords": [],
            "composition": "",
            "character_refs": []
        },
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_session.add(shot)
    test_session.commit()
    
    builder = ImageRenderInputBuilder(test_session)
    
    with pytest.raises(ValueError, match="empty render_prompt"):
        builder.build_input_for_shot(shot_id, episode_id)


def test_build_inputs_for_episode(test_session):
    """Test building inputs for all shots in an episode."""
    project_id = uuid4()
    episode_id = uuid4()
    
    # Create multiple shots
    shots = []
    for i in range(3):
        shot = ShotModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            scene_no=1,
            shot_no=i + 1,
            shot_code=f"S01_{i+1:03d}",
            status="draft",
            duration_ms=5000,
            camera_size="medium",
            camera_angle="eye-level",
            visual_constraints_jsonb={
                "render_prompt": f"Shot {i+1} render prompt with sufficient length",
                "style_keywords": ["cinematic"],
                "composition": "medium",
                "character_refs": []
            },
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        shots.append(shot)
        test_session.add(shot)
    
    test_session.commit()
    
    # Build inputs
    builder = ImageRenderInputBuilder(test_session)
    results = builder.build_inputs_for_episode(episode_id)
    
    # Verify results
    assert len(results) == 3
    assert all(r.episode_id == episode_id for r in results)
    assert [r.shot_no for r in results] == [1, 2, 3]


def test_merge_prompt_with_anchors_no_characters(test_session):
    """Test merging prompt with no characters."""
    builder = ImageRenderInputBuilder(test_session)
    
    prompt = "A beautiful landscape"
    character_refs = []
    character_profile = None
    
    enhanced_prompt, anchors = builder._merge_prompt_with_anchors(
        prompt, character_refs, character_profile
    )
    
    assert enhanced_prompt == prompt
    assert anchors == {}


def test_merge_prompt_with_anchors_with_characters(test_session):
    """Test merging prompt with character visual anchors."""
    builder = ImageRenderInputBuilder(test_session)
    
    prompt = "A room scene"
    character_refs = ["Alice", "Bob"]
    character_profile = {
        "characters": [
            {
                "name": "Alice",
                "visual_anchor": "tall woman with blue hair"
            },
            {
                "name": "Bob",
                "visual_anchor": "short man with red jacket"
            }
        ]
    }
    
    enhanced_prompt, anchors = builder._merge_prompt_with_anchors(
        prompt, character_refs, character_profile
    )
    
    # Check that anchors were extracted
    assert "Alice" in anchors
    assert "Bob" in anchors
    assert anchors["Alice"] == "tall woman with blue hair"
    assert anchors["Bob"] == "short man with red jacket"
    
    # Check that prompt was enhanced
    assert "Alice" in enhanced_prompt or "blue hair" in enhanced_prompt
    assert "Bob" in enhanced_prompt or "red jacket" in enhanced_prompt


def test_merge_prompt_with_anchors_already_present(test_session):
    """Test merging when anchor keywords already in prompt."""
    builder = ImageRenderInputBuilder(test_session)
    
    prompt = "A tall woman with blue hair stands in the room"
    character_refs = ["Alice"]
    character_profile = {
        "characters": [
            {
                "name": "Alice",
                "visual_anchor": "tall woman with blue hair"
            }
        ]
    }
    
    enhanced_prompt, anchors = builder._merge_prompt_with_anchors(
        prompt, character_refs, character_profile
    )
    
    # Anchors should still be extracted
    assert "Alice" in anchors
    
    # Prompt should not be duplicated (keywords already present)
    # The prompt should remain similar in length
    assert len(enhanced_prompt) < len(prompt) * 1.5


if __name__ == "__main__":
    print("Run with pytest: pytest apps/api/tests/unit/test_image_render_input_builder.py -v")
