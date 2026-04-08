"""
Unit tests for Shot Repository.

Tests Requirements:
- 1.1: Shot model completeness
- 4.1: Shot and visual_spec association
- 4.5: Version control
"""
import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.db.models import ProjectModel, EpisodeModel, ShotModel
from app.repositories.shot_repository import ShotRepository


@pytest.fixture
def test_project(test_session: Session):
    """Create a test project."""
    project = ProjectModel(
        id=uuid.uuid4(),
        name="Test Project",
        source_mode="original",
        target_platform="mobile",
        status="draft"
    )
    test_session.add(project)
    test_session.commit()
    test_session.refresh(project)
    return project


@pytest.fixture
def test_episode(test_session: Session, test_project):
    """Create a test episode."""
    episode = EpisodeModel(
        id=uuid.uuid4(),
        project_id=test_project.id,
        episode_no=1,
        title="Test Episode",
        status="draft",
        current_stage="storyboard",
        target_duration_sec=60
    )
    test_session.add(episode)
    test_session.commit()
    test_session.refresh(episode)
    return episode


@pytest.fixture
def shot_repository(test_session: Session):
    """Create a shot repository instance."""
    return ShotRepository(test_session)


def test_create_shot(shot_repository, test_project, test_episode):
    """Test creating a single shot."""
    shot_data = {
        "project_id": test_project.id,
        "episode_id": test_episode.id,
        "scene_no": 1,
        "shot_no": 1,
        "shot_code": "S01_001",
        "status": "draft",
        "duration_ms": 3000,
        "camera_size": "medium",
        "camera_angle": "eye-level",
        "movement_type": "static",
        "characters_jsonb": ["Alice", "Bob"],
        "action_text": "Alice talks to Bob",
        "dialogue_text": "Hello Bob!",
        "visual_constraints_jsonb": {
            "render_prompt": "A medium shot of Alice talking to Bob",
            "style_keywords": ["anime", "colorful"],
            "composition": "rule-of-thirds",
            "character_refs": ["Alice", "Bob"]
        },
        "version": 1
    }
    
    shot = shot_repository.create_shot(shot_data)
    
    assert shot.id is not None
    assert shot.scene_no == 1
    assert shot.shot_no == 1
    assert shot.shot_code == "S01_001"
    assert shot.duration_ms == 3000
    assert shot.version == 1
    assert shot.visual_constraints_jsonb["render_prompt"] == "A medium shot of Alice talking to Bob"


def test_create_many_shots(shot_repository, test_project, test_episode):
    """Test creating multiple shots at once."""
    shots_data = [
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 1,
            "shot_no": i,
            "shot_code": f"S01_{i:03d}",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {
                "render_prompt": f"Shot {i}",
                "style_keywords": [],
                "composition": "centered",
                "character_refs": []
            },
            "version": 1
        }
        for i in range(1, 4)
    ]
    
    shots = shot_repository.create_many(shots_data)
    
    assert len(shots) == 3
    assert shots[0].shot_no == 1
    assert shots[1].shot_no == 2
    assert shots[2].shot_no == 3


def test_get_by_id(shot_repository, test_project, test_episode):
    """Test retrieving a shot by ID."""
    shot_data = {
        "project_id": test_project.id,
        "episode_id": test_episode.id,
        "scene_no": 1,
        "shot_no": 1,
        "shot_code": "S01_001",
        "status": "draft",
        "duration_ms": 3000,
        "visual_constraints_jsonb": {},
        "version": 1
    }
    
    created_shot = shot_repository.create_shot(shot_data)
    retrieved_shot = shot_repository.get_by_id(created_shot.id)
    
    assert retrieved_shot is not None
    assert retrieved_shot.id == created_shot.id
    assert retrieved_shot.shot_code == "S01_001"


def test_list_current_for_episode_sorted(shot_repository, test_project, test_episode):
    """Test listing shots for an episode, sorted by scene_no and shot_no."""
    shots_data = [
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 2,
            "shot_no": 1,
            "shot_code": "S02_001",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {},
            "version": 1
        },
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 1,
            "shot_no": 2,
            "shot_code": "S01_002",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {},
            "version": 1
        },
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 1,
            "shot_no": 1,
            "shot_code": "S01_001",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {},
            "version": 1
        }
    ]
    
    shot_repository.create_many(shots_data)
    shots = shot_repository.list_current_for_episode(test_episode.id)
    
    assert len(shots) == 3
    # Should be sorted by scene_no, then shot_no
    assert shots[0].shot_code == "S01_001"
    assert shots[1].shot_code == "S01_002"
    assert shots[2].shot_code == "S02_001"


def test_version_control(shot_repository, test_project, test_episode):
    """Test version control - creating multiple versions of shots."""
    # Create version 1
    shots_v1 = [
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 1,
            "shot_no": 1,
            "shot_code": "S01_001",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {"render_prompt": "Version 1"},
            "version": 1
        }
    ]
    shot_repository.create_many(shots_v1)
    
    # Create version 2
    shots_v2 = [
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 1,
            "shot_no": 1,
            "shot_code": "S01_001",
            "status": "draft",
            "duration_ms": 3500,
            "visual_constraints_jsonb": {"render_prompt": "Version 2"},
            "version": 2
        }
    ]
    shot_repository.create_many(shots_v2)
    
    # Get latest version
    latest_version = shot_repository.latest_version_for_episode(test_episode.id)
    assert latest_version == 2
    
    # List current (latest version only)
    current_shots = shot_repository.list_current_for_episode(test_episode.id)
    assert len(current_shots) == 1
    assert current_shots[0].version == 2
    assert current_shots[0].duration_ms == 3500
    
    # List all versions
    all_shots = shot_repository.list_for_episode(test_episode.id)
    assert len(all_shots) == 2


def test_batch_query(shot_repository, test_project, test_episode):
    """Test batch querying multiple shots."""
    # Create 10 shots
    shots_data = [
        {
            "project_id": test_project.id,
            "episode_id": test_episode.id,
            "scene_no": 1,
            "shot_no": i,
            "shot_code": f"S01_{i:03d}",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {},
            "version": 1
        }
        for i in range(1, 11)
    ]
    
    shot_repository.create_many(shots_data)
    shots = shot_repository.list_current_for_episode(test_episode.id)
    
    assert len(shots) == 10
    # Verify they're sorted
    for i, shot in enumerate(shots, 1):
        assert shot.shot_no == i
