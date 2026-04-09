"""
Unit tests for AssetService and AssetRepository

Tests the primary asset selection logic and asset management.

Requirements tested:
- 8.1: Asset has shot_id field
- 8.4: Query shot's assets
- 8.5: Query shot's primary asset
- 10.2: Select primary asset
- 10.3: Ensure only one primary asset per shot
- 10.4: Record selection operation
"""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.db.models import ProjectModel, EpisodeModel
from app.services.asset_service import AssetService
from app.repositories.asset_repository import AssetRepository


@pytest.fixture
def test_project(test_session: Session):
    """Create a test project."""
    project = ProjectModel(
        id=uuid4(),
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
        id=uuid4(),
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


def test_create_asset_with_shot_id(test_session, test_project, test_episode):
    """Test creating an asset with shot_id field (Requirement 8.1)."""
    asset_service = AssetService(test_session)
    shot_id = uuid4()
    
    asset = asset_service.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe.png",
        mime_type="image/png",
        size_bytes=1024,
        width=1920,
        height=1080,
    )
    
    assert asset.id is not None
    assert asset.shot_id == shot_id
    assert asset.asset_type == "keyframe"
    assert asset.is_selected is False


def test_get_assets_by_shot(test_session, test_project, test_episode):
    """Test querying all assets for a shot (Requirement 8.4)."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    
    # Create multiple assets for the same shot
    asset1 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe1.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    asset2 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe2.png",
        mime_type="image/png",
        size_bytes=2048,
    )
    
    # Create asset for different shot
    other_shot_id = uuid4()
    asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=other_shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe3.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    test_session.commit()
    
    # Query assets for the first shot
    assets = asset_repo.get_assets_by_shot(shot_id)
    
    assert len(assets) == 2
    assert all(a.shot_id == shot_id for a in assets)
    # Should be ordered by created_at descending
    assert assets[0].id == asset2.id
    assert assets[1].id == asset1.id


def test_get_assets_by_shot_filtered_by_type(test_session, test_project, test_episode):
    """Test querying assets filtered by type (Requirement 8.4)."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    
    # Create assets of different types
    asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="audio",
        storage_key="s3://bucket/audio.mp3",
        mime_type="audio/mpeg",
        size_bytes=2048,
    )
    
    test_session.commit()
    
    # Query only keyframe assets
    keyframe_assets = asset_repo.get_assets_by_shot(shot_id, asset_type="keyframe")
    assert len(keyframe_assets) == 1
    assert keyframe_assets[0].asset_type == "keyframe"
    
    # Query only audio assets
    audio_assets = asset_repo.get_assets_by_shot(shot_id, asset_type="audio")
    assert len(audio_assets) == 1
    assert audio_assets[0].asset_type == "audio"


def test_get_selected_asset_by_shot(test_session, test_project, test_episode):
    """Test querying the primary asset for a shot (Requirement 8.5)."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    
    # Create assets, one selected
    asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe1.png",
        mime_type="image/png",
        size_bytes=1024,
        is_selected=False,
    )
    
    selected_asset = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe2.png",
        mime_type="image/png",
        size_bytes=2048,
        is_selected=True,
    )
    
    test_session.commit()
    
    # Query the selected asset
    result = asset_repo.get_selected_asset_by_shot(shot_id)
    
    assert result is not None
    assert result.id == selected_asset.id
    assert result.is_selected is True


def test_update_selected_asset(test_session, test_project, test_episode):
    """Test updating the primary asset (Requirements 10.2, 10.3)."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    
    # Create multiple assets
    asset1 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe1.png",
        mime_type="image/png",
        size_bytes=1024,
        is_selected=True,
    )
    
    asset2 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe2.png",
        mime_type="image/png",
        size_bytes=2048,
        is_selected=False,
    )
    
    test_session.commit()
    
    # Update selection to asset2
    updated_asset = asset_repo.update_selected_asset(shot_id, asset2.id)
    test_session.commit()
    
    # Verify asset2 is now selected
    assert updated_asset.id == asset2.id
    assert updated_asset.is_selected is True
    
    # Verify asset1 is no longer selected
    test_session.refresh(asset1)
    assert asset1.is_selected is False
    
    # Verify only one asset is selected
    selected_assets = [
        a for a in asset_repo.get_assets_by_shot(shot_id)
        if a.is_selected
    ]
    assert len(selected_assets) == 1
    assert selected_assets[0].id == asset2.id


def test_update_selected_asset_ensures_uniqueness(test_session, test_project, test_episode):
    """Test that only one asset can be primary per shot (Requirement 10.3)."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    
    # Create three assets, all initially selected (shouldn't happen in practice)
    asset1 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe1.png",
        mime_type="image/png",
        size_bytes=1024,
        is_selected=True,
    )
    
    asset2 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe2.png",
        mime_type="image/png",
        size_bytes=2048,
        is_selected=True,
    )
    
    asset3 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe3.png",
        mime_type="image/png",
        size_bytes=3072,
        is_selected=True,
    )
    
    test_session.commit()
    
    # Update selection to asset2
    asset_repo.update_selected_asset(shot_id, asset2.id)
    test_session.commit()
    
    # Verify only asset2 is selected
    test_session.refresh(asset1)
    test_session.refresh(asset2)
    test_session.refresh(asset3)
    
    assert asset1.is_selected is False
    assert asset2.is_selected is True
    assert asset3.is_selected is False


def test_select_primary_asset_records_selection(test_session, test_project, test_episode):
    """Test that selection operation is recorded (Requirement 10.4)."""
    asset_service = AssetService(test_session)
    shot_id = uuid4()
    
    # Create an asset
    asset = asset_service.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    test_session.commit()
    
    # Select the asset
    selected_asset = asset_service.select_primary_asset(
        shot_id=shot_id,
        asset_id=asset.id,
        selected_by="test_user"
    )
    
    test_session.commit()
    
    # Verify selection was recorded in metadata
    assert selected_asset.is_selected is True
    assert "selection_history" in selected_asset.metadata_jsonb
    
    history = selected_asset.metadata_jsonb["selection_history"]
    assert len(history) == 1
    assert history[0]["selected_by"] == "test_user"
    assert "selected_at" in history[0]


def test_update_selected_asset_validation(test_session, test_project, test_episode):
    """Test validation when updating selected asset."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    other_shot_id = uuid4()
    
    # Create asset for different shot
    other_asset = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=other_shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    test_session.commit()
    
    # Try to select asset from different shot
    with pytest.raises(ValueError, match="does not belong to shot"):
        asset_repo.update_selected_asset(shot_id, other_asset.id)
    
    # Try to select non-existent asset
    fake_asset_id = uuid4()
    with pytest.raises(ValueError, match="not found"):
        asset_repo.update_selected_asset(shot_id, fake_asset_id)


def test_select_primary_asset_by_type(test_session, test_project, test_episode):
    """Test selecting primary asset filtered by type."""
    asset_repo = AssetRepository(test_session)
    shot_id = uuid4()
    
    # Create assets of different types
    keyframe1 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe1.png",
        mime_type="image/png",
        size_bytes=1024,
        is_selected=True,
    )
    
    audio1 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="audio",
        storage_key="s3://bucket/audio1.mp3",
        mime_type="audio/mpeg",
        size_bytes=2048,
        is_selected=True,
    )
    
    keyframe2 = asset_repo.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe2.png",
        mime_type="image/png",
        size_bytes=1024,
        is_selected=False,
    )
    
    test_session.commit()
    
    # Update keyframe selection
    asset_repo.update_selected_asset(shot_id, keyframe2.id, asset_type="keyframe")
    test_session.commit()
    
    # Verify keyframe2 is selected, keyframe1 is not
    test_session.refresh(keyframe1)
    test_session.refresh(keyframe2)
    test_session.refresh(audio1)
    
    assert keyframe1.is_selected is False
    assert keyframe2.is_selected is True
    # Audio should still be selected (different type)
    assert audio1.is_selected is True



def test_get_candidate_assets(test_session, test_project, test_episode):
    """Test getting candidate assets for a shot (Requirement 8.3)."""
    asset_service = AssetService(test_session)
    shot_id = uuid4()
    
    # Create multiple assets for the same shot
    asset1 = asset_service.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe1.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    asset2 = asset_service.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe2.png",
        mime_type="image/png",
        size_bytes=2048,
    )
    
    test_session.commit()
    
    # Get candidate assets
    candidates = asset_service.get_candidate_assets(shot_id)
    
    assert len(candidates) == 2
    assert all(a.shot_id == shot_id for a in candidates)


def test_get_selection_history(test_session, test_project, test_episode):
    """Test getting selection history for an asset (Requirement 8.4)."""
    asset_service = AssetService(test_session)
    shot_id = uuid4()
    
    # Create an asset
    asset = asset_service.create_asset(
        project_id=test_project.id,
        episode_id=test_episode.id,
        shot_id=shot_id,
        asset_type="keyframe",
        storage_key="s3://bucket/keyframe.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    
    test_session.commit()
    
    # Initially no history
    history = asset_service.get_selection_history(asset.id)
    assert len(history) == 0
    
    # Select the asset
    asset_service.select_primary_asset(
        shot_id=shot_id,
        asset_id=asset.id,
        selected_by="user1"
    )
    test_session.commit()
    
    # Check history
    history = asset_service.get_selection_history(asset.id)
    assert len(history) == 1
    assert history[0]["selected_by"] == "user1"
    
    # Select again
    asset_service.select_primary_asset(
        shot_id=shot_id,
        asset_id=asset.id,
        selected_by="user2"
    )
    test_session.commit()
    
    # Check history has both entries
    history = asset_service.get_selection_history(asset.id)
    assert len(history) == 2
    assert history[0]["selected_by"] == "user1"
    assert history[1]["selected_by"] == "user2"


def test_get_selection_history_nonexistent_asset(test_session):
    """Test getting selection history for non-existent asset."""
    asset_service = AssetService(test_session)
    fake_asset_id = uuid4()
    
    with pytest.raises(ValueError, match="not found"):
        asset_service.get_selection_history(fake_asset_id)
