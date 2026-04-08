"""
Unit tests for workspace service functionality.
Tests the build_workspace method with shot details and visual_spec references.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.services.store import DatabaseStore


def test_workspace_includes_shot_details(test_session):
    """Test that workspace response includes detailed shot information."""
    store = DatabaseStore(test_session)
    
    # Create a project
    from app.schemas.project import CreateProjectRequest, CreateEpisodeRequest
    project_req = CreateProjectRequest(
        name="Test Project",
        source_mode="original",
        target_platform="mobile",
    )
    project = store.create_project(project_req)
    
    # Create an episode
    episode_req = CreateEpisodeRequest(
        episode_no=1,
        title="Test Episode",
        target_duration_sec=60,
    )
    episode = store.create_episode(project.id, episode_req)
    
    # Create a visual_spec document
    visual_spec_doc = store.documents.create(
        project_id=project.id,
        episode_id=episode.id,
        document_type="visual_spec",
        version=1,
        status="approved",
        title="Visual Spec v1",
        content_jsonb={
            "shots": [
                {
                    "shot_id": "S01_001",
                    "render_prompt": "A beautiful sunset scene",
                    "character_refs": ["Alice"],
                    "style_keywords": ["cinematic", "warm"],
                    "composition": "wide"
                }
            ],
            "overall_duration_ms": 5000,
            "shot_count": 1,
            "visual_style": "cinematic",
            "camera_strategy": "dynamic"
        },
        commit=True
    )
    
    # Create a shot
    shot_data = {
        "project_id": project.id,
        "episode_id": episode.id,
        "scene_no": 1,
        "shot_no": 1,
        "shot_code": "S01_001",
        "status": "draft",
        "duration_ms": 5000,
        "camera_size": "wide",
        "camera_angle": "eye-level",
        "movement_type": "static",
        "characters_jsonb": ["Alice"],
        "action_text": "Alice walks into the sunset",
        "dialogue_text": "What a beautiful day!",
        "visual_constraints_jsonb": {
            "render_prompt": "A beautiful sunset scene with Alice walking",
            "style_keywords": ["cinematic", "warm"],
            "composition": "wide",
            "character_refs": ["Alice"]
        },
        "version": 1,
    }
    shot = store.shots.create_shot(shot_data, commit=True)
    
    # Build workspace
    workspace = store.build_workspace(project.id, episode.id)
    
    # Verify workspace is not None
    assert workspace is not None
    
    # Verify shots are included
    assert len(workspace.shots) == 1
    
    # Verify shot details
    shot_summary = workspace.shots[0]
    assert shot_summary.id == shot.id
    assert shot_summary.code == "S01_001"
    assert shot_summary.scene_no == 1
    assert shot_summary.shot_no == 1
    assert shot_summary.duration_ms == 5000
    assert shot_summary.status == "draft"
    assert shot_summary.camera_size == "wide"
    assert shot_summary.camera_angle == "eye-level"
    assert shot_summary.movement_type == "static"
    assert shot_summary.characters == ["Alice"]
    assert shot_summary.version == 1
    
    # Verify visual_constraints_summary
    assert shot_summary.visual_constraints_summary is not None
    assert "render_prompt" in shot_summary.visual_constraints_summary
    assert shot_summary.visual_constraints_summary["style_keywords"] == ["cinematic", "warm"]
    assert shot_summary.visual_constraints_summary["composition"] == "wide"
    assert shot_summary.visual_constraints_summary["character_refs"] == ["Alice"]
    
    # Verify visual_spec reference
    assert shot_summary.visual_spec_doc_id == visual_spec_doc.id
    
    # Verify metadata includes visual_spec_doc_id
    assert workspace.metadata["visual_spec_doc_id"] == str(visual_spec_doc.id)


def test_workspace_with_multiple_shots_sorted(test_session):
    """Test that workspace returns shots sorted by scene_no and shot_no."""
    store = DatabaseStore(test_session)
    
    # Create a project and episode
    from app.schemas.project import CreateProjectRequest, CreateEpisodeRequest
    project_req = CreateProjectRequest(
        name="Test Project",
        source_mode="original",
        target_platform="mobile",
    )
    project = store.create_project(project_req)
    
    episode_req = CreateEpisodeRequest(
        episode_no=1,
        title="Test Episode",
        target_duration_sec=60,
    )
    episode = store.create_episode(project.id, episode_req)
    
    # Create multiple shots in random order
    shots_data = [
        {
            "project_id": project.id,
            "episode_id": episode.id,
            "scene_no": 2,
            "shot_no": 1,
            "shot_code": "S02_001",
            "status": "draft",
            "duration_ms": 3000,
            "visual_constraints_jsonb": {"render_prompt": "Scene 2 Shot 1"},
            "version": 1,
        },
        {
            "project_id": project.id,
            "episode_id": episode.id,
            "scene_no": 1,
            "shot_no": 2,
            "shot_code": "S01_002",
            "status": "draft",
            "duration_ms": 2000,
            "visual_constraints_jsonb": {"render_prompt": "Scene 1 Shot 2"},
            "version": 1,
        },
        {
            "project_id": project.id,
            "episode_id": episode.id,
            "scene_no": 1,
            "shot_no": 1,
            "shot_code": "S01_001",
            "status": "draft",
            "duration_ms": 1000,
            "visual_constraints_jsonb": {"render_prompt": "Scene 1 Shot 1"},
            "version": 1,
        },
    ]
    
    for shot_data in shots_data:
        store.shots.create_shot(shot_data, commit=True)
    
    # Build workspace
    workspace = store.build_workspace(project.id, episode.id)
    
    # Verify shots are sorted correctly
    assert len(workspace.shots) == 3
    assert workspace.shots[0].code == "S01_001"
    assert workspace.shots[1].code == "S01_002"
    assert workspace.shots[2].code == "S02_001"


def test_workspace_with_no_visual_spec(test_session):
    """Test that workspace works when there's no visual_spec document."""
    store = DatabaseStore(test_session)
    
    # Create a project and episode
    from app.schemas.project import CreateProjectRequest, CreateEpisodeRequest
    project_req = CreateProjectRequest(
        name="Test Project",
        source_mode="original",
        target_platform="mobile",
    )
    project = store.create_project(project_req)
    
    episode_req = CreateEpisodeRequest(
        episode_no=1,
        title="Test Episode",
        target_duration_sec=60,
    )
    episode = store.create_episode(project.id, episode_req)
    
    # Create a shot without visual_spec
    shot_data = {
        "project_id": project.id,
        "episode_id": episode.id,
        "scene_no": 1,
        "shot_no": 1,
        "shot_code": "S01_001",
        "status": "draft",
        "duration_ms": 5000,
        "visual_constraints_jsonb": {"render_prompt": "Test prompt"},
        "version": 1,
    }
    store.shots.create_shot(shot_data, commit=True)
    
    # Build workspace
    workspace = store.build_workspace(project.id, episode.id)
    
    # Verify workspace is built successfully
    assert workspace is not None
    assert len(workspace.shots) == 1
    
    # Verify visual_spec_doc_id is None
    assert workspace.shots[0].visual_spec_doc_id is None
    assert workspace.metadata["visual_spec_doc_id"] is None


def test_workspace_with_latest_visual_spec_version(test_session):
    """Test that workspace uses the latest version of visual_spec."""
    store = DatabaseStore(test_session)
    
    # Create a project and episode
    from app.schemas.project import CreateProjectRequest, CreateEpisodeRequest
    project_req = CreateProjectRequest(
        name="Test Project",
        source_mode="original",
        target_platform="mobile",
    )
    project = store.create_project(project_req)
    
    episode_req = CreateEpisodeRequest(
        episode_no=1,
        title="Test Episode",
        target_duration_sec=60,
    )
    episode = store.create_episode(project.id, episode_req)
    
    # Create multiple versions of visual_spec
    visual_spec_v1 = store.documents.create(
        project_id=project.id,
        episode_id=episode.id,
        document_type="visual_spec",
        version=1,
        status="approved",
        content_jsonb={"shots": []},
        commit=True
    )
    
    visual_spec_v2 = store.documents.create(
        project_id=project.id,
        episode_id=episode.id,
        document_type="visual_spec",
        version=2,
        status="approved",
        content_jsonb={"shots": []},
        commit=True
    )
    
    # Create a shot
    shot_data = {
        "project_id": project.id,
        "episode_id": episode.id,
        "scene_no": 1,
        "shot_no": 1,
        "shot_code": "S01_001",
        "status": "draft",
        "duration_ms": 5000,
        "visual_constraints_jsonb": {"render_prompt": "Test prompt"},
        "version": 1,
    }
    store.shots.create_shot(shot_data, commit=True)
    
    # Build workspace
    workspace = store.build_workspace(project.id, episode.id)
    
    # Verify workspace uses the latest visual_spec version
    assert workspace is not None
    assert workspace.shots[0].visual_spec_doc_id == visual_spec_v2.id
    assert workspace.metadata["visual_spec_doc_id"] == str(visual_spec_v2.id)
