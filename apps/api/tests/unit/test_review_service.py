"""
Unit tests for Review Gate Service

Tests Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.services.review_service import ReviewGateService
from app.repositories.review_repository import ReviewRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.db.models import StageTaskModel, WorkflowRunModel, ReviewDecisionModel


class TestReviewGateService:
    """Test suite for ReviewGateService"""
    
    def test_pause_for_review_success(self, test_session):
        """
        Test pausing workflow for review.
        
        Validates Requirements 5.1, 5.2:
        - When Stage is marked review_required, pause workflow
        - Update StageTask review_status to "pending"
        """
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        
        # Create workflow
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="running",
        )
        test_session.add(workflow)
        test_session.flush()
        
        # Create stage task with review_required=True
        stage_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="brief",
            task_status="completed",
            worker_kind="agent",
            review_required=True,
            review_status=None,
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute
        result = service.pause_for_review(stage_task.id)
        
        # Verify
        assert result.task_status == "review_pending"
        assert result.review_status == "pending"
        
        # Verify workflow status
        test_session.refresh(workflow)
        assert workflow.status == "waiting_review"
    
    def test_pause_for_review_not_required(self, test_session):
        """Test that pausing fails if stage is not marked for review."""
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="running",
        )
        test_session.add(workflow)
        test_session.flush()
        
        # Create stage task with review_required=False
        stage_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="script",
            task_status="completed",
            worker_kind="agent",
            review_required=False,
            review_status=None,
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute and verify error
        with pytest.raises(ValueError, match="not marked for review"):
            service.pause_for_review(stage_task.id)
    
    def test_submit_review_approved(self, test_session):
        """
        Test submitting an approved review decision.
        
        Validates Requirements 5.3, 5.4, 6.1, 6.2:
        - Create ReviewDecision record
        - Record reviewer_user_id and decision
        - approved: Resume workflow execution
        """
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        reviewer_id = uuid4()
        
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="waiting_review",
        )
        test_session.add(workflow)
        test_session.flush()
        
        stage_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="brief",
            task_status="review_pending",
            worker_kind="agent",
            review_required=True,
            review_status="pending",
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute
        review = service.submit_review(
            stage_task_id=stage_task.id,
            reviewer_user_id=reviewer_id,
            decision="approved",
            comment="Looks good!",
        )
        
        # Verify review record
        assert review.decision == "approved"
        assert review.reviewer_user_id == reviewer_id
        assert review.comment_text == "Looks good!"
        assert review.stage_task_id == stage_task.id
        
        # Verify stage task updated
        test_session.refresh(stage_task)
        assert stage_task.review_status == "approved"
        assert stage_task.task_status == "completed"
        
        # Verify workflow resumed
        test_session.refresh(workflow)
        assert workflow.status == "running"
    
    def test_submit_review_rejected(self, test_session):
        """
        Test submitting a rejected review decision.
        
        Validates Requirements 5.5, 6.3:
        - rejected: Terminate workflow
        """
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        reviewer_id = uuid4()
        
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="waiting_review",
        )
        test_session.add(workflow)
        test_session.flush()
        
        stage_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="brief",
            task_status="review_pending",
            worker_kind="agent",
            review_required=True,
            review_status="pending",
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute
        review = service.submit_review(
            stage_task_id=stage_task.id,
            reviewer_user_id=reviewer_id,
            decision="rejected",
            comment="Not acceptable",
        )
        
        # Verify review record
        assert review.decision == "rejected"
        assert review.comment_text == "Not acceptable"
        
        # Verify stage task updated
        test_session.refresh(stage_task)
        assert stage_task.review_status == "rejected"
        assert stage_task.task_status == "failed"
        
        # Verify workflow terminated
        test_session.refresh(workflow)
        assert workflow.status == "failed"
        assert "Review rejected" in workflow.failure_reason
    
    def test_submit_review_revision_required(self, test_session):
        """
        Test submitting a revision_required review decision.
        
        Validates Requirements 6.3, 6.4, 6.5:
        - revision_required: Mark for rerun
        - Record rerun parameters in payload
        """
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        reviewer_id = uuid4()
        
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="waiting_review",
        )
        test_session.add(workflow)
        test_session.flush()
        
        stage_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="storyboard",
            task_status="review_pending",
            worker_kind="agent",
            review_required=True,
            review_status="pending",
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute with rerun payload
        rerun_payload = {
            "rerun_from_stage": "storyboard",
            "reason": "Need to adjust character expressions",
        }
        review = service.submit_review(
            stage_task_id=stage_task.id,
            reviewer_user_id=reviewer_id,
            decision="revision_required",
            comment="Please revise the storyboard",
            payload=rerun_payload,
        )
        
        # Verify review record
        assert review.decision == "revision_required"
        assert review.comment_text == "Please revise the storyboard"
        assert review.payload_jsonb == rerun_payload
        
        # Verify stage task updated
        test_session.refresh(stage_task)
        assert stage_task.review_status == "revision_required"
        
        # Workflow should still be waiting_review (rerun will be triggered separately)
        test_session.refresh(workflow)
        assert workflow.status == "waiting_review"
    
    def test_submit_review_invalid_decision(self, test_session):
        """Test that invalid decision values are rejected."""
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="waiting_review",
        )
        test_session.add(workflow)
        test_session.flush()
        
        stage_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="brief",
            task_status="review_pending",
            worker_kind="agent",
            review_required=True,
            review_status="pending",
        )
        test_session.add(stage_task)
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute with invalid decision
        with pytest.raises(ValueError, match="Invalid decision"):
            service.submit_review(
                stage_task_id=stage_task.id,
                reviewer_user_id=uuid4(),
                decision="invalid_decision",
            )
    
    def test_get_pending_reviews(self, test_session):
        """Test getting all pending reviews for an episode."""
        # Setup
        project_id = uuid4()
        episode_id = uuid4()
        
        workflow = WorkflowRunModel(
            id=uuid4(),
            project_id=project_id,
            episode_id=episode_id,
            workflow_kind="episode",
            temporal_workflow_id=f"test-{uuid4()}",
            temporal_run_id=str(uuid4()),
            status="waiting_review",
        )
        test_session.add(workflow)
        test_session.flush()
        
        # Create multiple stage tasks with different review statuses
        pending_task1 = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="brief",
            task_status="review_pending",
            worker_kind="agent",
            review_required=True,
            review_status="pending",
        )
        
        pending_task2 = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="storyboard",
            task_status="review_pending",
            worker_kind="agent",
            review_required=True,
            review_status="pending",
        )
        
        approved_task = StageTaskModel(
            id=uuid4(),
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type="script",
            task_status="completed",
            worker_kind="agent",
            review_required=True,
            review_status="approved",
        )
        
        test_session.add_all([pending_task1, pending_task2, approved_task])
        test_session.commit()
        
        # Create service
        review_repo = ReviewRepository(test_session)
        stage_task_repo = StageTaskRepository(test_session)
        workflow_repo = WorkflowRepository(test_session)
        service = ReviewGateService(test_session, review_repo, stage_task_repo, workflow_repo)
        
        # Execute
        pending_reviews = service.get_pending_reviews(episode_id)
        
        # Verify - should only return pending tasks
        assert len(pending_reviews) == 2
        pending_ids = {task.id for task in pending_reviews}
        assert pending_task1.id in pending_ids
        assert pending_task2.id in pending_ids
        assert approved_task.id not in pending_ids
