"""
Unit tests for Subtitle Generation Stage

Tests subtitle generation logic including:
- VTT timestamp formatting
- Subtitle entry building from shots
- Text sanitization
- Full stage execution (success and failure paths)

Requirements tested:
- 4.1: Extract dialogue from script_draft and shots
- 4.2: Compute timeline from shot duration_ms
- 4.3: Generate VTT format
- 4.4: Upload subtitle file and create Asset record
- 4.5: Errors do not block subsequent stages
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import (
    ProjectModel,
    EpisodeModel,
    ShotModel,
    StageTaskModel,
    WorkflowRunModel,
)
from app.services.subtitle_generation_stage import (
    SubtitleGenerationStage,
    SubtitleEntry,
)
from app.services.object_storage_service import ObjectStorageService, UploadResult
from app.repositories.asset_repository import AssetRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_project(test_session: Session):
    project = ProjectModel(
        id=uuid4(),
        name="Subtitle Test Project",
        source_mode="original",
        target_platform="mobile",
        status="draft",
    )
    test_session.add(project)
    test_session.commit()
    test_session.refresh(project)
    return project


@pytest.fixture
def test_episode(test_session: Session, test_project):
    episode = EpisodeModel(
        id=uuid4(),
        project_id=test_project.id,
        episode_no=1,
        title="Subtitle Test Episode",
        status="draft",
        current_stage="subtitle_generation",
        target_duration_sec=60,
    )
    test_session.add(episode)
    test_session.commit()
    test_session.refresh(episode)
    return episode


@pytest.fixture
def test_workflow_run(test_session: Session, test_project, test_episode):
    wf = WorkflowRunModel(
        id=uuid4(),
        project_id=test_project.id,
        episode_id=test_episode.id,
        workflow_kind="media",
        temporal_workflow_id="subtitle-test-wf-123",
        temporal_run_id="subtitle-test-run-123",
        status="running",
    )
    test_session.add(wf)
    test_session.commit()
    test_session.refresh(wf)
    return wf


@pytest.fixture
def test_stage_task(test_session: Session, test_project, test_episode, test_workflow_run):
    task = StageTaskModel(
        id=uuid4(),
        workflow_run_id=test_workflow_run.id,
        project_id=test_project.id,
        episode_id=test_episode.id,
        stage_type="subtitle_generation",
        task_status="pending",
        worker_kind="media",
    )
    test_session.add(task)
    test_session.commit()
    test_session.refresh(task)
    return task


def _make_shot(test_session, project, episode, stage_task, scene_no, shot_no, duration_ms, dialogue=None):
    shot = ShotModel(
        id=uuid4(),
        project_id=project.id,
        episode_id=episode.id,
        stage_task_id=stage_task.id,
        scene_no=scene_no,
        shot_no=shot_no,
        shot_code=f"S{scene_no:02d}-{shot_no:03d}",
        status="draft",
        duration_ms=duration_ms,
        visual_constraints_jsonb={},
        dialogue_text=dialogue,
        version=1,
    )
    test_session.add(shot)
    test_session.commit()
    test_session.refresh(shot)
    return shot


def _make_storage_mock():
    mock = Mock(spec=ObjectStorageService)
    mock.generate_storage_key.return_value = "proj/ep/subtitle/20260408/test.vtt"
    mock.upload_file.return_value = UploadResult(
        storage_key="proj/ep/subtitle/20260408/test.vtt",
        url="http://storage.example.com/test.vtt",
        size_bytes=512,
    )
    return mock


# ---------------------------------------------------------------------------
# Unit tests: _ms_to_vtt_timestamp
# ---------------------------------------------------------------------------


def test_ms_to_vtt_timestamp_zero():
    assert SubtitleGenerationStage._ms_to_vtt_timestamp(0) == "00:00:00.000"


def test_ms_to_vtt_timestamp_one_second():
    assert SubtitleGenerationStage._ms_to_vtt_timestamp(1000) == "00:00:01.000"


def test_ms_to_vtt_timestamp_one_minute():
    assert SubtitleGenerationStage._ms_to_vtt_timestamp(60_000) == "00:01:00.000"


def test_ms_to_vtt_timestamp_one_hour():
    assert SubtitleGenerationStage._ms_to_vtt_timestamp(3_600_000) == "01:00:00.000"


def test_ms_to_vtt_timestamp_mixed():
    # 1h 2m 3s 456ms
    ms = 3_600_000 + 2 * 60_000 + 3_000 + 456
    assert SubtitleGenerationStage._ms_to_vtt_timestamp(ms) == "01:02:03.456"


def test_ms_to_vtt_timestamp_negative_clamped():
    # Negative values should be clamped to 0
    assert SubtitleGenerationStage._ms_to_vtt_timestamp(-500) == "00:00:00.000"


# ---------------------------------------------------------------------------
# Unit tests: _generate_vtt
# ---------------------------------------------------------------------------


def test_generate_vtt_starts_with_webvtt(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    entries = [SubtitleEntry(start_ms=0, end_ms=5000, text="Hello")]
    vtt = stage._generate_vtt(entries)
    assert vtt.startswith("WEBVTT")


def test_generate_vtt_contains_timestamp(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    entries = [SubtitleEntry(start_ms=0, end_ms=5000, text="Hello")]
    vtt = stage._generate_vtt(entries)
    assert "00:00:00.000 --> 00:00:05.000" in vtt


def test_generate_vtt_contains_text(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    entries = [SubtitleEntry(start_ms=0, end_ms=3000, text="Test dialogue")]
    vtt = stage._generate_vtt(entries)
    assert "Test dialogue" in vtt


def test_generate_vtt_multiple_entries_sequential(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    entries = [
        SubtitleEntry(start_ms=0, end_ms=3000, text="First"),
        SubtitleEntry(start_ms=3000, end_ms=6000, text="Second"),
    ]
    vtt = stage._generate_vtt(entries)
    assert "First" in vtt
    assert "Second" in vtt
    # Second entry starts where first ends
    assert "00:00:03.000 --> 00:00:06.000" in vtt


def test_generate_vtt_empty_entries(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    vtt = stage._generate_vtt([])
    assert vtt.startswith("WEBVTT")


# ---------------------------------------------------------------------------
# Unit tests: _sanitize_text
# ---------------------------------------------------------------------------


def test_sanitize_text_strips_whitespace(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    assert stage._sanitize_text("  hello  ") == "hello"


def test_sanitize_text_collapses_newlines(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    assert stage._sanitize_text("hello\nworld") == "hello world"


def test_sanitize_text_escapes_arrow(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    result = stage._sanitize_text("go --> there")
    assert "-->" not in result


def test_sanitize_text_empty(test_session, test_project, test_episode, test_stage_task):
    stage = SubtitleGenerationStage(db=test_session, storage_service=Mock())
    assert stage._sanitize_text("") == ""


# ---------------------------------------------------------------------------
# Integration tests: execute()
# ---------------------------------------------------------------------------


def test_execute_no_shots_returns_succeeded(
    test_session, test_project, test_episode, test_stage_task
):
    """Stage should succeed gracefully when there are no shots (Req 4.5)."""
    stage = SubtitleGenerationStage(
        db=test_session,
        storage_service=_make_storage_mock(),
    )
    result = stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
    )
    assert result.status == "succeeded"
    assert result.assets_created == 0
    assert result.shots_processed == 0


def test_execute_creates_asset_for_shots_with_dialogue(
    test_session, test_project, test_episode, test_stage_task
):
    """Stage should create one subtitle asset when shots have dialogue (Req 4.4)."""
    _make_shot(test_session, test_project, test_episode, test_stage_task, 1, 1, 5000, "Hello world")
    _make_shot(test_session, test_project, test_episode, test_stage_task, 1, 2, 3000, "Goodbye")

    mock_storage = _make_storage_mock()
    stage = SubtitleGenerationStage(db=test_session, storage_service=mock_storage)

    result = stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
    )

    assert result.status == "succeeded"
    assert result.assets_created == 1
    assert result.shots_processed == 2

    # Verify asset was persisted
    asset_repo = AssetRepository(test_session)
    assets = asset_repo.list_for_episode(test_episode.id)
    subtitle_assets = [a for a in assets if a.asset_type == "subtitle"]
    assert len(subtitle_assets) == 1
    assert subtitle_assets[0].mime_type == "text/vtt"
    assert subtitle_assets[0].is_selected is True


def test_execute_shots_without_dialogue_still_succeed(
    test_session, test_project, test_episode, test_stage_task
):
    """Shots with no dialogue produce no subtitle entries but stage still succeeds (Req 4.5)."""
    _make_shot(test_session, test_project, test_episode, test_stage_task, 1, 1, 5000, dialogue=None)

    mock_storage = _make_storage_mock()
    stage = SubtitleGenerationStage(db=test_session, storage_service=mock_storage)

    result = stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
    )

    # Stage succeeds; asset is still created (empty VTT is valid)
    assert result.status == "succeeded"
    assert result.shots_processed == 1


def test_execute_timeline_is_cumulative(
    test_session, test_project, test_episode, test_stage_task
):
    """Timeline should accumulate across shots (Req 4.2)."""
    _make_shot(test_session, test_project, test_episode, test_stage_task, 1, 1, 4000, "First")
    _make_shot(test_session, test_project, test_episode, test_stage_task, 1, 2, 6000, "Second")

    captured_vtt: list = []
    original_upload = None

    mock_storage = _make_storage_mock()

    # Intercept the VTT content written to the temp file
    import builtins
    original_open = builtins.open

    stage = SubtitleGenerationStage(db=test_session, storage_service=mock_storage)

    # Patch _generate_vtt to capture output
    original_gen = stage._generate_vtt

    def capturing_gen(entries):
        result = original_gen(entries)
        captured_vtt.append(result)
        return result

    stage._generate_vtt = capturing_gen

    stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
    )

    assert captured_vtt, "VTT was never generated"
    vtt = captured_vtt[0]

    # First shot: 0 -> 4000ms
    assert "00:00:00.000 --> 00:00:04.000" in vtt
    # Second shot: 4000 -> 10000ms
    assert "00:00:04.000 --> 00:00:10.000" in vtt


def test_execute_storage_failure_returns_failed(
    test_session, test_project, test_episode, test_stage_task
):
    """If storage upload fails, stage should return failed status (Req 4.5)."""
    _make_shot(test_session, test_project, test_episode, test_stage_task, 1, 1, 5000, "Hello")

    mock_storage = Mock(spec=ObjectStorageService)
    mock_storage.generate_storage_key.return_value = "some/key.vtt"
    mock_storage.upload_file.side_effect = RuntimeError("S3 unavailable")

    stage = SubtitleGenerationStage(db=test_session, storage_service=mock_storage)

    result = stage.execute(
        episode_id=test_episode.id,
        project_id=test_project.id,
        stage_task_id=test_stage_task.id,
    )

    assert result.status == "failed"
    assert len(result.errors) > 0
