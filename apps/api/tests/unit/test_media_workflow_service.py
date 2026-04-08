"""
Unit tests for MediaWorkflowService

Tests the orchestration of media pipeline stages.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.services.media_workflow_service import MediaWorkflowService, MediaWorkflowResult
from app.services.image_render_stage import StageExecutionResult
from app.services.subtitle_generation_stage import SubtitleGenerationResult
from app.services.tts_stage import TTSStageResult
from app.services.preview_export_stage import PreviewExportResult


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_image_render_stage():
    """Mock image render stage."""
    stage = Mock()
    stage.execute = AsyncMock(return_value=StageExecutionResult(
        status="succeeded",
        assets_created=5,
        shots_processed=5,
        shots_failed=0,
        errors=[],
        execution_time_ms=1000,
        metrics={"provider_calls": 5}
    ))
    return stage


@pytest.fixture
def mock_subtitle_stage():
    """Mock subtitle generation stage."""
    stage = Mock()
    stage.execute = Mock(return_value=SubtitleGenerationResult(
        status="succeeded",
        assets_created=1,
        shots_processed=5,
        errors=[],
        execution_time_ms=500,
        metrics={"subtitle_entries": 5}
    ))
    return stage


@pytest.fixture
def mock_tts_stage():
    """Mock TTS stage."""
    stage = Mock()
    stage.execute = AsyncMock(return_value=TTSStageResult(
        status="succeeded",
        assets_created=3,
        shots_processed=3,
        shots_failed=0,
        errors=[],
        execution_time_ms=2000,
        metrics={"provider_calls": 3}
    ))
    return stage


@pytest.fixture
def mock_preview_export_stage():
    """Mock preview export stage."""
    stage = Mock()
    stage.execute = Mock(return_value=PreviewExportResult(
        status="succeeded",
        assets_created=1,
        shots_collected=5,
        errors=[],
        execution_time_ms=3000,
        metrics={"preview_duration_ms": 15000}
    ))
    return stage


@pytest.fixture
def mock_stage_task_repo():
    """Mock stage task repository."""
    repo = Mock()
    repo.create = Mock(return_value=Mock(id=uuid4()))
    repo.update_status = Mock()
    repo.latest_by_stage = Mock(return_value=Mock(id=uuid4()))
    return repo


@pytest.fixture
def mock_workflow_repo():
    """Mock workflow repository."""
    repo = Mock()
    repo.update_status = Mock()
    return repo


@pytest.fixture
def media_workflow_service(
    mock_db,
    mock_image_render_stage,
    mock_subtitle_stage,
    mock_tts_stage,
    mock_preview_export_stage,
    mock_stage_task_repo,
    mock_workflow_repo,
):
    """Create MediaWorkflowService with mocked dependencies."""
    service = MediaWorkflowService(
        db=mock_db,
        image_render_stage=mock_image_render_stage,
        subtitle_stage=mock_subtitle_stage,
        tts_stage=mock_tts_stage,
        preview_export_stage=mock_preview_export_stage,
    )
    service.stage_task_repo = mock_stage_task_repo
    service.workflow_repo = mock_workflow_repo
    return service


@pytest.mark.asyncio
async def test_execute_media_chain_success(media_workflow_service):
    """Test successful execution of complete media chain."""
    # Arrange
    project = Mock(id=uuid4())
    episode = Mock(id=uuid4())
    workflow_run = Mock(id=uuid4())
    
    # Act
    result = await media_workflow_service.execute_media_chain(
        project=project,
        episode=episode,
        workflow_run=workflow_run,
    )
    
    # Assert
    assert result.status == "media_ready"
    assert len(result.stages_completed) == 4
    assert len(result.stages_failed) == 0
    assert result.total_assets_created == 10  # 5 + 1 + 3 + 1
    assert "image_render" in result.stages_completed
    assert "subtitle" in result.stages_completed
    assert "tts" in result.stages_completed
    assert "edit_export_preview" in result.stages_completed


@pytest.mark.asyncio
async def test_execute_media_chain_with_start_stage(media_workflow_service):
    """Test execution starting from a specific stage."""
    # Arrange
    project = Mock(id=uuid4())
    episode = Mock(id=uuid4())
    workflow_run = Mock(id=uuid4())
    
    # Act
    result = await media_workflow_service.execute_media_chain(
        project=project,
        episode=episode,
        workflow_run=workflow_run,
        start_stage="tts",
    )
    
    # Assert
    assert result.status == "media_ready"
    assert len(result.stages_completed) == 2  # tts and preview
    assert "image_render" not in result.stages_completed
    assert "subtitle" not in result.stages_completed
    assert "tts" in result.stages_completed
    assert "edit_export_preview" in result.stages_completed


@pytest.mark.asyncio
async def test_execute_media_chain_partial_success(
    media_workflow_service,
    mock_tts_stage,
):
    """Test handling of partial success (some stages fail)."""
    # Arrange
    project = Mock(id=uuid4())
    episode = Mock(id=uuid4())
    workflow_run = Mock(id=uuid4())
    
    # Make TTS stage fail
    mock_tts_stage.execute = AsyncMock(return_value=TTSStageResult(
        status="failed",
        assets_created=0,
        shots_processed=0,
        shots_failed=3,
        errors=["TTS provider error"],
        execution_time_ms=500,
        metrics={}
    ))
    
    # Act
    result = await media_workflow_service.execute_media_chain(
        project=project,
        episode=episode,
        workflow_run=workflow_run,
    )
    
    # Assert
    assert result.status == "media_partial"
    assert "tts" in result.stages_failed
    assert "image_render" in result.stages_completed
    assert "subtitle" in result.stages_completed
    # Preview should still execute despite TTS failure
    assert "edit_export_preview" in result.stages_completed


@pytest.mark.asyncio
async def test_execute_media_chain_critical_failure(
    media_workflow_service,
    mock_image_render_stage,
):
    """Test handling of critical stage failure (stops execution)."""
    # Arrange
    project = Mock(id=uuid4())
    episode = Mock(id=uuid4())
    workflow_run = Mock(id=uuid4())
    
    # Make image render stage fail completely
    mock_image_render_stage.execute = AsyncMock(return_value=StageExecutionResult(
        status="failed",
        assets_created=0,
        shots_processed=0,
        shots_failed=5,
        errors=["Image provider unavailable"],
        execution_time_ms=500,
        metrics={}
    ))
    
    # Act
    result = await media_workflow_service.execute_media_chain(
        project=project,
        episode=episode,
        workflow_run=workflow_run,
    )
    
    # Assert
    assert result.status == "media_failed"
    assert "image_render" in result.stages_failed
    assert len(result.stages_completed) == 0
    # Subsequent stages should not execute
    assert "subtitle" not in result.stages_completed
    assert "tts" not in result.stages_completed


@pytest.mark.asyncio
async def test_stage_task_creation(
    media_workflow_service,
    mock_stage_task_repo,
):
    """Test that StageTask records are created for each stage."""
    # Arrange
    project = Mock(id=uuid4())
    episode = Mock(id=uuid4())
    workflow_run = Mock(id=uuid4())
    
    # Act
    await media_workflow_service.execute_media_chain(
        project=project,
        episode=episode,
        workflow_run=workflow_run,
    )
    
    # Assert
    assert mock_stage_task_repo.create.call_count == 4
    
    # Verify each stage type was created
    created_stages = [
        call.kwargs['stage_type']
        for call in mock_stage_task_repo.create.call_args_list
    ]
    assert "image_render" in created_stages
    assert "subtitle" in created_stages
    assert "tts" in created_stages
    assert "edit_export_preview" in created_stages


@pytest.mark.asyncio
async def test_workflow_status_update(
    media_workflow_service,
    mock_workflow_repo,
):
    """Test that WorkflowRun status is updated correctly."""
    # Arrange
    project = Mock(id=uuid4())
    episode = Mock(id=uuid4())
    workflow_run = Mock(id=uuid4())
    
    # Act
    await media_workflow_service.execute_media_chain(
        project=project,
        episode=episode,
        workflow_run=workflow_run,
    )
    
    # Assert
    mock_workflow_repo.update_status.assert_called_once()
    call_args = mock_workflow_repo.update_status.call_args
    assert call_args[0][0] == workflow_run.id
    assert call_args.kwargs['status'] == "media_ready"


def test_get_stages_to_execute_all(media_workflow_service):
    """Test getting all stages when no start_stage specified."""
    stages = media_workflow_service._get_stages_to_execute(None)
    assert stages == ["image_render", "subtitle", "tts", "edit_export_preview"]


def test_get_stages_to_execute_from_middle(media_workflow_service):
    """Test getting stages starting from middle of sequence."""
    stages = media_workflow_service._get_stages_to_execute("subtitle")
    assert stages == ["subtitle", "tts", "edit_export_preview"]


def test_should_continue_after_partial_success(media_workflow_service):
    """Test continuation decision for partial success."""
    result = {'status': 'partial_success', 'assets_created': 3}
    should_continue = media_workflow_service._should_continue_after_failure(
        "image_render",
        result
    )
    assert should_continue is True


def test_should_continue_after_critical_failure(media_workflow_service):
    """Test continuation decision for critical stage failure."""
    result = {'status': 'failed', 'assets_created': 0}
    should_continue = media_workflow_service._should_continue_after_failure(
        "image_render",
        result
    )
    assert should_continue is False


def test_should_continue_after_non_critical_failure(media_workflow_service):
    """Test continuation decision for non-critical stage failure."""
    result = {'status': 'failed', 'assets_created': 0}
    should_continue = media_workflow_service._should_continue_after_failure(
        "subtitle",
        result
    )
    assert should_continue is True


def test_determine_final_status_all_success(media_workflow_service):
    """Test final status determination when all stages succeed."""
    status = media_workflow_service._determine_final_status(
        stages_completed=["image_render", "subtitle", "tts", "edit_export_preview"],
        stages_failed=[],
        total_stages=4
    )
    assert status == "media_ready"


def test_determine_final_status_partial(media_workflow_service):
    """Test final status determination for partial success."""
    status = media_workflow_service._determine_final_status(
        stages_completed=["image_render", "subtitle"],
        stages_failed=["tts"],
        total_stages=4
    )
    assert status == "media_partial"


def test_determine_final_status_all_failed(media_workflow_service):
    """Test final status determination when all stages fail."""
    status = media_workflow_service._determine_final_status(
        stages_completed=[],
        stages_failed=["image_render", "subtitle", "tts", "edit_export_preview"],
        total_stages=4
    )
    assert status == "media_failed"
