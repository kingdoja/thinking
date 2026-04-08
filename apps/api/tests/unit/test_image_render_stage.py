"""
Unit tests for Image Render Stage

Tests the image rendering stage logic including parallel processing,
retry mechanism, and asset creation.

Requirements tested:
- 2.1: Build inputs for shots
- 2.2: Call image provider with correct parameters
- 2.3: Upload images to object storage
- 2.4: Create asset records
- 2.5: Handle failures gracefully
- 11.1: Parallel processing
- 12.1: Retry with exponential backoff
- 12.2: Distinguish temporary vs permanent errors
"""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.db.models import ProjectModel, EpisodeModel, ShotModel, StageTaskModel, WorkflowRunModel
from app.services.image_render_stage import ImageRenderStage, StageExecutionResult
from app.services.image_render_input_builder import ImageRenderInputBuilder, ImageRenderInput
from app.providers.image_provider import ImageGenerationResult, ProviderError
from app.services.object_storage_service import ObjectStorageService, UploadResult
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
        current_stage="image_render",
        target_duration_sec=60
    )
    test_session.add(episode)
    test_session.commit()
    test_session.refresh(episode)
    return episode


@pytest.fixture
def test_workflow_run(test_session: Session, test_project, test_episode):
    """Create a test workflow run."""
    workflow_run = WorkflowRunModel(
        id=uuid4(),
        project_id=test_project.id,
        episode_id=test_episode.id,
        workflow_kind="media",
        temporal_workflow_id="test-workflow-123",
        temporal_run_id="test-run-123",
        status="running"
    )
    test_session.add(workflow_run)
    test_session.commit()
    test_session.refresh(workflow_run)
    return workflow_run


@pytest.fixture
def test_stage_task(test_session: Session, test_project, test_episode, test_workflow_run):
    """Create a test stage task."""
    stage_task = StageTaskModel(
        id=uuid4(),
        workflow_run_id=test_workflow_run.id,
        project_id=test_project.id,
        episode_id=test_episode.id,
        stage_type="image_render",
        task_status="pending",
        worker_kind="media"
    )
    test_session.add(stage_task)
    test_session.commit()
    test_session.refresh(stage_task)
    return stage_task


@pytest.fixture
def test_shot(test_session: Session, test_project, test_episode, test_stage_task):
    """Create a test shot with visual constraints."""
    shot = ShotModel(
        id=uuid4(),
        project_id=test_project.id,
        episode_id=test_episode.id,
        stage_task_id=test_stage_task.id,
        scene_no=1,
        shot_no=1,
        shot_code="S01-001",
        status="draft",
        duration_ms=5000,
        camera_size="medium",
        camera_angle="eye-level",
        visual_constraints_jsonb={
            "render_prompt": "A beautiful sunset over mountains",
            "style_keywords": ["cinematic", "dramatic"],
            "composition": "rule of thirds",
            "character_refs": []
        },
        version=1
    )
    test_session.add(shot)
    test_session.commit()
    test_session.refresh(shot)
    return shot


@pytest.mark.asyncio
async def test_execute_stage_success(
    test_session,
    test_project,
    test_episode,
    test_stage_task,
    test_shot
):
    """Test successful execution of image render stage (Requirements 2.1, 2.2, 2.3, 2.4)."""
    # Mock dependencies
    mock_provider = Mock()
    mock_provider.generate_image = Mock(return_value=ImageGenerationResult(
        success=True,
        image_data=b"fake_image_data",
        image_url="http://example.com/image.png",
        width=1080,
        height=1920,
        format="png",
        shot_id=test_shot.id,
        provider_metadata={"model": "test_model"}
    ))
    
    mock_storage = Mock(spec=ObjectStorageService)
    mock_storage.generate_storage_key = Mock(return_value="test/key/image.png")
    mock_storage.upload_file = Mock(return_value=UploadResult(
        storage_key="test/key/image.png",
        url="http://storage.example.com/test/key/image.png",
        size_bytes=len(b"fake_image_data")
    ))
    
    input_builder = ImageRenderInputBuilder(test_session)
    
    # Create stage
    stage = ImageRenderStage(
        db=test_session,
        image_provider=mock_provider,
        storage_service=mock_storage,
        input_builder=input_builder
    )
    
    # Execute stage
    result = await stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
        max_concurrent=5
    )
    
    # Verify result
    assert result.status == "succeeded"
    assert result.assets_created == 1
    assert result.shots_processed == 1
    assert result.shots_failed == 0
    assert len(result.errors) == 0
    
    # Verify provider was called
    assert mock_provider.generate_image.called
    
    # Verify storage was called
    assert mock_storage.upload_file.called
    
    # Verify asset was created
    asset_repo = AssetRepository(test_session)
    assets = asset_repo.get_assets_by_shot(test_shot.id, asset_type="keyframe")
    assert len(assets) == 1
    assert assets[0].storage_key == "test/key/image.png"
    assert assets[0].is_selected is True


@pytest.mark.asyncio
async def test_execute_stage_with_failure(
    test_session,
    test_project,
    test_episode,
    test_stage_task,
    test_shot
):
    """Test stage execution with provider failure (Requirement 2.5)."""
    # Mock provider that fails
    mock_provider = Mock()
    mock_provider.generate_image = Mock(side_effect=ProviderError(
        message="Provider error",
        provider_name="test_provider",
        is_retryable=False
    ))
    
    mock_storage = Mock(spec=ObjectStorageService)
    input_builder = ImageRenderInputBuilder(test_session)
    
    # Create stage
    stage = ImageRenderStage(
        db=test_session,
        image_provider=mock_provider,
        storage_service=mock_storage,
        input_builder=input_builder
    )
    
    # Execute stage
    result = await stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
        max_concurrent=5
    )
    
    # Verify result shows failure
    assert result.status == "failed"
    assert result.assets_created == 0
    assert result.shots_processed == 0
    assert result.shots_failed == 1
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_parallel_generation(test_session, test_project, test_episode, test_stage_task):
    """Test parallel image generation (Requirement 11.1)."""
    # Create multiple shots
    shots = []
    for i in range(3):
        shot = ShotModel(
            id=uuid4(),
            project_id=test_project.id,
            episode_id=test_episode.id,
            stage_task_id=test_stage_task.id,
            scene_no=1,
            shot_no=i + 1,
            shot_code=f"S01-{i+1:03d}",
            status="draft",
            duration_ms=5000,
            visual_constraints_jsonb={
                "render_prompt": f"Test prompt {i}",
                "style_keywords": ["test"],
                "composition": "test",
                "character_refs": []
            },
            version=1
        )
        test_session.add(shot)
        shots.append(shot)
    
    test_session.commit()
    
    # Mock provider
    call_count = 0
    
    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return ImageGenerationResult(
            success=True,
            image_data=b"fake_image_data",
            width=1080,
            height=1920,
            format="png",
            shot_id=kwargs.get('shot_id')
        )
    
    mock_provider = Mock()
    mock_provider.generate_image = Mock(side_effect=mock_generate)
    
    mock_storage = Mock(spec=ObjectStorageService)
    mock_storage.generate_storage_key = Mock(return_value="test/key/image.png")
    mock_storage.upload_file = Mock(return_value=UploadResult(
        storage_key="test/key/image.png",
        url="http://storage.example.com/test/key/image.png",
        size_bytes=100
    ))
    
    input_builder = ImageRenderInputBuilder(test_session)
    
    # Create stage
    stage = ImageRenderStage(
        db=test_session,
        image_provider=mock_provider,
        storage_service=mock_storage,
        input_builder=input_builder
    )
    
    # Execute stage
    result = await stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
        max_concurrent=2
    )
    
    # Verify all shots were processed
    assert result.shots_processed == 3
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_mechanism(test_session, test_project, test_episode, test_stage_task, test_shot):
    """Test retry mechanism with exponential backoff (Requirements 12.1, 12.2)."""
    # Mock provider that fails twice then succeeds
    call_count = 0
    
    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ProviderError(
                message="Temporary error",
                provider_name="test_provider",
                is_retryable=True
            )
        return ImageGenerationResult(
            success=True,
            image_data=b"fake_image_data",
            width=1080,
            height=1920,
            format="png",
            shot_id=kwargs.get('shot_id')
        )
    
    mock_provider = Mock()
    mock_provider.generate_image = Mock(side_effect=mock_generate)
    
    mock_storage = Mock(spec=ObjectStorageService)
    mock_storage.generate_storage_key = Mock(return_value="test/key/image.png")
    mock_storage.upload_file = Mock(return_value=UploadResult(
        storage_key="test/key/image.png",
        url="http://storage.example.com/test/key/image.png",
        size_bytes=100
    ))
    
    input_builder = ImageRenderInputBuilder(test_session)
    
    # Create stage
    stage = ImageRenderStage(
        db=test_session,
        image_provider=mock_provider,
        storage_service=mock_storage,
        input_builder=input_builder
    )
    
    # Execute stage
    result = await stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
        max_concurrent=5
    )
    
    # Verify success after retries
    assert result.status == "succeeded"
    assert result.shots_processed == 1
    assert call_count == 3  # Failed twice, succeeded on third attempt


@pytest.mark.asyncio
async def test_permanent_error_no_retry(
    test_session,
    test_project,
    test_episode,
    test_stage_task,
    test_shot
):
    """Test that permanent errors are not retried (Requirement 12.2)."""
    call_count = 0
    
    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise ProviderError(
            message="Permanent error",
            provider_name="test_provider",
            is_retryable=False  # Not retryable
        )
    
    mock_provider = Mock()
    mock_provider.generate_image = Mock(side_effect=mock_generate)
    
    mock_storage = Mock(spec=ObjectStorageService)
    input_builder = ImageRenderInputBuilder(test_session)
    
    # Create stage
    stage = ImageRenderStage(
        db=test_session,
        image_provider=mock_provider,
        storage_service=mock_storage,
        input_builder=input_builder
    )
    
    # Execute stage
    result = await stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
        max_concurrent=5
    )
    
    # Verify only one attempt was made
    assert call_count == 1
    assert result.status == "failed"
