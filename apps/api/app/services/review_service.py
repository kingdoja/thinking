"""
Review Gate Service

Implements Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5

This service handles the human review workflow:
- Pausing workflows for review
- Submitting review decisions
- Processing review decisions (approve/reject/revision)
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ReviewDecisionModel, StageTaskModel, WorkflowRunModel
from app.repositories.review_repository import ReviewRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.repositories.workflow_repository import WorkflowRepository


class ReviewGateService:
    """
    Review Gate Service handles human review workflow.
    
    Responsibilities:
    1. Pause workflow for review
    2. Handle review submissions
    3. Process review decisions
    4. Resume or terminate workflows
    """
    
    def __init__(
        self,
        db: Session,
        review_repo: ReviewRepository,
        stage_task_repo: StageTaskRepository,
        workflow_repo: WorkflowRepository,
    ) -> None:
        self.db = db
        self.review_repo = review_repo
        self.stage_task_repo = stage_task_repo
        self.workflow_repo = workflow_repo
    
    def pause_for_review(self, stage_task_id: UUID) -> StageTaskModel:
        """
        Pause workflow for human review.
        
        Implements Requirements 5.1, 5.2:
        - When Stage is marked review_required, pause workflow
        - Update StageTask review_status to "pending"
        
        Args:
            stage_task_id: StageTask ID to pause for review
            
        Returns:
            Updated StageTask model
            
        Raises:
            ValueError: If stage task not found or not review_required
        """
        stage_task = self.stage_task_repo.get(stage_task_id)
        if stage_task is None:
            raise ValueError(f"StageTask {stage_task_id} not found")
        
        if not stage_task.review_required:
            raise ValueError(f"StageTask {stage_task_id} is not marked for review")
        
        # Update stage task status
        stage_task = self.stage_task_repo.update_status(
            stage_task_id,
            task_status="review_pending",
            review_status="pending",
        )
        
        # Update workflow status to waiting_review
        self.workflow_repo.update_status(
            stage_task.workflow_run_id,
            status="waiting_review",
        )
        
        return stage_task
    
    def submit_review(
        self,
        stage_task_id: UUID,
        reviewer_user_id: Optional[UUID],
        decision: str,
        comment: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> ReviewDecisionModel:
        """
        Submit a review decision.
        
        Implements Requirements 5.3, 6.1, 6.2:
        - Create ReviewDecision record
        - Record reviewer_user_id and decision
        - Save comment_text and payload
        
        Args:
            stage_task_id: StageTask ID being reviewed
            reviewer_user_id: User ID of reviewer (optional for system reviews)
            decision: Review decision (approved/rejected/revision_required)
            comment: Review comment (optional)
            payload: Additional data (optional, e.g., rerun parameters)
            
        Returns:
            Created ReviewDecision model
            
        Raises:
            ValueError: If stage task not found or invalid decision
        """
        # Validate decision
        valid_decisions = {"approved", "rejected", "revision_required"}
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision: {decision}. Must be one of {valid_decisions}")
        
        # Get stage task
        stage_task = self.stage_task_repo.get(stage_task_id)
        if stage_task is None:
            raise ValueError(f"StageTask {stage_task_id} not found")
        
        # Create review decision
        review = self.review_repo.create(
            project_id=stage_task.project_id,
            episode_id=stage_task.episode_id,
            stage_task_id=stage_task_id,
            reviewer_user_id=reviewer_user_id,
            decision=decision,
            comment_text=comment,
            payload_jsonb=payload or {},
            commit=False,
        )
        
        # Process the decision
        self.process_decision(review)
        
        # Commit transaction
        self.db.commit()
        self.db.refresh(review)
        
        return review
    
    def process_decision(self, review: ReviewDecisionModel) -> None:
        """
        Process a review decision.
        
        Implements Requirements 5.4, 5.5, 6.3, 6.4, 6.5:
        - approved: Resume workflow execution
        - rejected: Terminate workflow
        - revision_required: Trigger rerun (handled by caller)
        
        Args:
            review: ReviewDecision model to process
        """
        stage_task = self.stage_task_repo.get(review.stage_task_id)
        if stage_task is None:
            raise ValueError(f"StageTask {review.stage_task_id} not found")
        
        if review.decision == "approved":
            # Approve: Update review status and resume workflow
            self.stage_task_repo.update_review_status(
                review.stage_task_id,
                review_status="approved",
                commit=False,
            )
            
            # Update stage task to completed
            self.stage_task_repo.update_status(
                review.stage_task_id,
                task_status="completed",
                commit=False,
            )
            
            # Resume workflow
            self.workflow_repo.update_status(
                stage_task.workflow_run_id,
                status="running",
                commit=False,
            )
            
        elif review.decision == "rejected":
            # Reject: Update review status and terminate workflow
            self.stage_task_repo.update_review_status(
                review.stage_task_id,
                review_status="rejected",
                commit=False,
            )
            
            # Update stage task to failed
            self.stage_task_repo.update_status(
                review.stage_task_id,
                task_status="failed",
                error_message=f"Rejected by reviewer: {review.comment_text or 'No comment'}",
                commit=False,
            )
            
            # Terminate workflow
            self.workflow_repo.update_status(
                stage_task.workflow_run_id,
                status="failed",
                failure_reason=f"Review rejected: {review.comment_text or 'No comment'}",
                commit=False,
            )
            
        elif review.decision == "revision_required":
            # Revision required: Update review status
            # Rerun will be triggered by caller using payload data
            self.stage_task_repo.update_review_status(
                review.stage_task_id,
                review_status="revision_required",
                commit=False,
            )
            
            # Keep workflow in waiting_review state
            # Caller will trigger rerun which will create new workflow
    
    def resume_workflow(self, stage_task_id: UUID) -> WorkflowRunModel:
        """
        Resume workflow execution after review approval.
        
        This method is called after a review is approved to continue
        workflow execution from the next stage.
        
        Args:
            stage_task_id: StageTask ID that was approved
            
        Returns:
            Updated WorkflowRun model
            
        Raises:
            ValueError: If stage task not found or not approved
        """
        stage_task = self.stage_task_repo.get(stage_task_id)
        if stage_task is None:
            raise ValueError(f"StageTask {stage_task_id} not found")
        
        if stage_task.review_status != "approved":
            raise ValueError(
                f"Cannot resume workflow - stage task review status is {stage_task.review_status}, "
                "expected 'approved'"
            )
        
        # Get workflow
        workflow = self.db.get(WorkflowRunModel, stage_task.workflow_run_id)
        if workflow is None:
            raise ValueError(f"WorkflowRun {stage_task.workflow_run_id} not found")
        
        # Resume workflow
        workflow = self.workflow_repo.update_status(
            workflow.id,
            status="running",
        )
        
        return workflow
    
    def get_pending_reviews(self, episode_id: UUID) -> list:
        """
        Get all pending reviews for an episode.
        
        Args:
            episode_id: Episode ID
            
        Returns:
            List of StageTask models with pending reviews
        """
        from sqlalchemy import select
        from app.db.models import StageTaskModel
        
        stmt = (
            select(StageTaskModel)
            .where(
                StageTaskModel.episode_id == episode_id,
                StageTaskModel.review_status == "pending",
            )
            .order_by(StageTaskModel.created_at.desc())
        )
        
        return list(self.db.scalars(stmt).all())
