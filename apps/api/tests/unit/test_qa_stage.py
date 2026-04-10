"""
Unit tests for QA Stage Service

Tests the QA Stage's ability to:
1. Execute QA checks in workflow context
2. Update StageTask with results
3. Decide workflow continuation
"""

import pytest
from uuid import uuid4
from datetime import datetime

from app.services.qa_stage import QAStage, QAStageResult
from app.db.models import ProjectModel, EpisodeModel, WorkflowRunModel, StageTaskModel


class TestQAStage:
    """Test QA Stage functionality."""
    
    def test_qa_stage_execution_with_no_issues(self, test_session):
        """Test QA stage execution when no issues are found."""
        # Arrange - Create test data
        project = ProjectModel(
            name="Test Project",
            source_mode="ai_generated",
            target_platform="mobile",
            status="active",
        )
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(
            project_id=project.id,
            episode_no=1,
            title="Test Episode",
            target_duration_sec=60,
            status="draft",
        )
        test_session.add(episode)
        test_session.flush()
        
        workflow_run = WorkflowRunModel(
            project_id=project.id,
            episode_id=episode.id,
            workflow_kind="episode",
            temporal_workflow_id="test-workflow-1",
            temporal_run_id="test-run-1",
            status="running",
        )
        test_session.add(workflow_run)
        test_session.flush()
        
        stage_task = StageTaskModel(
            workflow_run_id=workflow_run.id,
            project_id=project.id,
            episode_id=episode.id,
            stage_type="qa",
            task_status="pending",
            worker_kind="qa",
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Act
        qa_stage = QAStage(test_session)
        result = qa_stage.execute(
            episode_id=episode.id,
            project_id=project.id,
            stage_task_id=stage_task.id,
        )
        
        # Assert
        assert result.status == "passed"
        assert result.should_block is False
        assert len(result.errors) == 0
        assert result.execution_time_ms > 0
        
        # Verify stage task was updated
        test_session.refresh(stage_task)
        assert stage_task.task_status == "succeeded"
        assert stage_task.finished_at is not None
        assert stage_task.metrics_jsonb is not None
        assert stage_task.metrics_jsonb.get('checks_executed') == 2  # rule + semantic
    
    def test_qa_stage_updates_metrics(self, test_session):
        """Test that QA stage properly updates StageTask metrics."""
        # Arrange
        project = ProjectModel(
            name="Test Project",
            source_mode="ai_generated",
            target_platform="mobile",
            status="active",
        )
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(
            project_id=project.id,
            episode_no=1,
            title="Test Episode",
            target_duration_sec=60,
            status="draft",
        )
        test_session.add(episode)
        test_session.flush()
        
        workflow_run = WorkflowRunModel(
            project_id=project.id,
            episode_id=episode.id,
            workflow_kind="episode",
            temporal_workflow_id="test-workflow-2",
            temporal_run_id="test-run-2",
            status="running",
        )
        test_session.add(workflow_run)
        test_session.flush()
        
        stage_task = StageTaskModel(
            workflow_run_id=workflow_run.id,
            project_id=project.id,
            episode_id=episode.id,
            stage_type="qa",
            task_status="pending",
            worker_kind="qa",
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Act
        qa_stage = QAStage(test_session)
        result = qa_stage.execute(
            episode_id=episode.id,
            project_id=project.id,
            stage_task_id=stage_task.id,
        )
        
        # Assert - Check metrics
        test_session.refresh(stage_task)
        metrics = stage_task.metrics_jsonb
        
        assert 'execution_time_ms' in metrics
        assert 'checks_executed' in metrics
        assert 'checks_passed' in metrics
        assert 'checks_failed' in metrics
        assert 'total_issues' in metrics
        assert 'critical_issues' in metrics
        assert 'major_issues' in metrics
        
        assert metrics['execution_time_ms'] > 0
        assert metrics['checks_executed'] >= 0
