"""
Media Workflow Service

Orchestrates the execution of media pipeline stages in the correct sequence:
1. Image Render Stage
2. Subtitle Generation Stage
3. TTS Stage
4. Preview Export Stage

Implements Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import EpisodeModel, ProjectModel, WorkflowRunModel
from app.repositories.stage_task_repository import StageTaskRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.image_render_stage import ImageRenderStage, StageExecutionResult
from app.services.subtitle_generation_stage import SubtitleGenerationStage, SubtitleGenerationResult
from app.services.tts_stage import TTSStage, TTSStageResult
from app.services.preview_export_stage import PreviewExportStage, PreviewExportResult


# Media stage execution sequence (Requirement 10.2)
MEDIA_STAGE_SEQUENCE = [
    "image_render",
    "subtitle",
    "tts",
    "edit_export_preview",
    "qa",  # QA check after media chain (Iteration 5)
]


@dataclass
class MediaWorkflowResult:
    """Result of the complete media workflow execution."""
    status: str  # succeeded, partial_success, failed
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    total_assets_created: int = 0
    execution_time_ms: int = 0
    stage_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class MediaWorkflowService:
    """
    Media Workflow Service - orchestrates media pipeline stage execution.
    
    Responsibilities:
    1. Define and enforce stage execution order (Requirement 10.2)
    2. Create StageTask records for each stage (Requirement 10.5)
    3. Execute stages sequentially (Requirement 10.1)
    4. Handle stage failures and decide continuation (Requirement 10.3, 10.4)
    5. Update WorkflowRun status (Requirement 10.4)
    
    Implements Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """
    
    def __init__(
        self,
        db: Session,
        image_render_stage: ImageRenderStage,
        subtitle_stage: SubtitleGenerationStage,
        tts_stage: TTSStage,
        preview_export_stage: PreviewExportStage,
        qa_stage=None,  # Optional QA stage (Iteration 5)
    ):
        """
        Initialize the Media Workflow Service.
        
        Args:
            db: Database session
            image_render_stage: Image render stage instance
            subtitle_stage: Subtitle generation stage instance
            tts_stage: TTS stage instance
            preview_export_stage: Preview export stage instance
            qa_stage: QA stage instance (optional)
        """
        self.db = db
        self.image_render_stage = image_render_stage
        self.subtitle_stage = subtitle_stage
        self.tts_stage = tts_stage
        self.preview_export_stage = preview_export_stage
        self.qa_stage = qa_stage
        
        self.stage_task_repo = StageTaskRepository(db)
        self.workflow_repo = WorkflowRepository(db)
    
    async def execute_media_chain(
        self,
        project: ProjectModel,
        episode: EpisodeModel,
        workflow_run: WorkflowRunModel,
        start_stage: Optional[str] = None,
    ) -> MediaWorkflowResult:
        """
        Execute the complete media workflow chain for an episode.
        
        Implements Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
        
        Args:
            project: Project model
            episode: Episode model
            workflow_run: WorkflowRun model
            start_stage: Optional stage to start from (for reruns)
            
        Returns:
            MediaWorkflowResult with execution details
        """
        import time
        start_time = time.time()
        
        # Determine which stages to execute (Requirement 10.2)
        stages_to_execute = self._get_stages_to_execute(start_stage)
        
        stages_completed: List[str] = []
        stages_failed: List[str] = []
        total_assets_created = 0
        stage_results: Dict[str, Any] = {}
        errors: List[str] = []
        
        # Execute each stage in sequence (Requirement 10.1, 10.2)
        for stage_type in stages_to_execute:
            try:
                # Create StageTask record (Requirement 10.5)
                stage_task = self._create_stage_task(
                    workflow_run_id=workflow_run.id,
                    project_id=project.id,
                    episode_id=episode.id,
                    stage_type=stage_type,
                )
                
                # Execute the stage
                result = await self._execute_stage(
                    stage_type=stage_type,
                    project_id=project.id,
                    episode_id=episode.id,
                    stage_task_id=stage_task.id,
                )
                
                # Store result
                stage_results[stage_type] = result
                
                # Update metrics in stage task (Requirement 10.5)
                self._update_stage_task_metrics(stage_task.id, result)
                
                # Check if stage succeeded (Requirement 10.3)
                if result.get('status') in ['succeeded', 'partial_success']:
                    stages_completed.append(stage_type)
                    total_assets_created += result.get('assets_created', 0)
                    
                    # Check if this stage requires review (Requirements 5.1, 5.2)
                    if stage_task.review_required:
                        # Update stage task to review_pending
                        self.stage_task_repo.update_status(
                            stage_task.id,
                            "review_pending",
                            review_status="pending",
                            commit=False,
                        )
                        
                        # Update workflow status to waiting_review
                        self.workflow_repo.update_status(
                            workflow_run.id,
                            "waiting_review",
                            commit=True,
                        )
                        
                        # Stop execution and return partial result
                        execution_time_ms = int((time.time() - start_time) * 1000)
                        return MediaWorkflowResult(
                            status="waiting_review",
                            stages_completed=stages_completed,
                            stages_failed=stages_failed,
                            total_assets_created=total_assets_created,
                            execution_time_ms=execution_time_ms,
                            stage_results=stage_results,
                            errors=errors,
                        )
                else:
                    stages_failed.append(stage_type)
                    errors.extend(result.get('errors', []))
                    
                    # Decide whether to continue (Requirement 10.3)
                    if not self._should_continue_after_failure(stage_type, result):
                        break
                        
            except Exception as e:
                # Handle unexpected errors (Requirement 10.3)
                error_msg = f"Stage {stage_type} failed with exception: {str(e)}"
                errors.append(error_msg)
                stages_failed.append(stage_type)
                
                # Mark stage task as failed with metrics (Requirement 10.5)
                stage_task = self.stage_task_repo.latest_by_stage(episode.id, stage_type)
                if stage_task:
                    # Record failure metrics
                    failure_metrics = {
                        'execution_time_ms': 0,
                        'assets_created': 0,
                        'shots_processed': 0,
                        'shots_failed': 0,
                        'error_type': type(e).__name__,
                    }
                    self.stage_task_repo.update_metrics(
                        stage_task.id,
                        metrics=failure_metrics,
                        commit=False,
                    )
                    self.stage_task_repo.update_status(
                        stage_task.id,
                        "failed",
                        finished_at=datetime.utcnow(),
                        error_message=str(e),
                        commit=True,
                    )
                
                # Stop execution on unexpected errors
                break
        
        # Calculate final status
        execution_time_ms = int((time.time() - start_time) * 1000)
        final_status = self._determine_final_status(
            stages_completed=stages_completed,
            stages_failed=stages_failed,
            total_stages=len(stages_to_execute),
        )
        
        # Update WorkflowRun status (Requirement 10.4)
        self._update_workflow_status(
            workflow_run_id=workflow_run.id,
            status=final_status,
            errors=errors,
        )
        
        return MediaWorkflowResult(
            status=final_status,
            stages_completed=stages_completed,
            stages_failed=stages_failed,
            total_assets_created=total_assets_created,
            execution_time_ms=execution_time_ms,
            stage_results=stage_results,
            errors=errors,
        )
    
    def _get_stages_to_execute(self, start_stage: Optional[str]) -> List[str]:
        """
        Get the list of stages to execute based on start_stage.
        
        Implements Requirement 10.2
        
        Args:
            start_stage: Optional stage to start from
            
        Returns:
            List of stage types to execute in order
        """
        if start_stage is None:
            return MEDIA_STAGE_SEQUENCE.copy()
        
        # Find the index of start_stage
        try:
            start_index = MEDIA_STAGE_SEQUENCE.index(start_stage)
            return MEDIA_STAGE_SEQUENCE[start_index:]
        except ValueError:
            # If start_stage is not in the sequence, execute all stages
            return MEDIA_STAGE_SEQUENCE.copy()
    
    def _create_stage_task(
        self,
        workflow_run_id: UUID,
        project_id: UUID,
        episode_id: UUID,
        stage_type: str,
    ):
        """
        Create a StageTask record for a media stage.
        
        Implements Requirement 10.5
        
        Args:
            workflow_run_id: WorkflowRun ID
            project_id: Project ID
            episode_id: Episode ID
            stage_type: Stage type
            
        Returns:
            Created StageTask model
        """
        stage_task = self.stage_task_repo.create(
            workflow_run_id=workflow_run_id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type=stage_type,
            task_status="pending",
            worker_kind="media",
            agent_name=None,
            input_ref_jsonb=[],
            output_ref_jsonb=[],
            review_required=False,
            review_status=None,
            started_at=None,
            metrics_jsonb={},
            commit=True,
        )
        
        # Update status to running when created
        self.stage_task_repo.update_status(
            stage_task.id,
            "running",
            started_at=datetime.utcnow(),
            commit=True,
        )
        
        return stage_task
    
    async def _execute_stage(
        self,
        stage_type: str,
        project_id: UUID,
        episode_id: UUID,
        stage_task_id: UUID,
    ) -> Dict[str, Any]:
        """
        Execute a specific media stage.
        
        Implements Requirement 10.1
        
        Args:
            stage_type: Type of stage to execute
            project_id: Project ID
            episode_id: Episode ID
            stage_task_id: StageTask ID
            
        Returns:
            Dictionary with execution result
        """
        if stage_type == "image_render":
            result = await self.image_render_stage.execute(
                episode_id=episode_id,
                project_id=project_id,
                stage_task_id=stage_task_id,
            )
            return self._convert_stage_result(result)
            
        elif stage_type == "subtitle":
            result = self.subtitle_stage.execute(
                episode_id=episode_id,
                project_id=project_id,
                stage_task_id=stage_task_id,
            )
            return self._convert_subtitle_result(result)
            
        elif stage_type == "tts":
            result = await self.tts_stage.execute(
                episode_id=episode_id,
                project_id=project_id,
                stage_task_id=stage_task_id,
            )
            return self._convert_tts_result(result)
            
        elif stage_type == "edit_export_preview":
            result = self.preview_export_stage.execute(
                episode_id=episode_id,
                project_id=project_id,
                stage_task_id=stage_task_id,
            )
            return self._convert_preview_result(result)
        
        elif stage_type == "qa":
            # Execute QA stage (Iteration 5)
            if self.qa_stage is None:
                # QA stage not configured, skip
                return {
                    'status': 'succeeded',
                    'assets_created': 0,
                    'shots_processed': 0,
                    'shots_failed': 0,
                    'errors': [],
                    'execution_time_ms': 0,
                    'metrics': {},
                }
            
            result = self.qa_stage.execute(
                episode_id=episode_id,
                project_id=project_id,
                stage_task_id=stage_task_id,
            )
            return self._convert_qa_result(result)
            
        else:
            raise ValueError(f"Unknown stage type: {stage_type}")
    
    def _convert_stage_result(self, result: StageExecutionResult) -> Dict[str, Any]:
        """Convert StageExecutionResult to dictionary."""
        return {
            'status': result.status,
            'assets_created': result.assets_created,
            'shots_processed': result.shots_processed,
            'shots_failed': result.shots_failed,
            'errors': result.errors,
            'execution_time_ms': result.execution_time_ms,
            'metrics': result.metrics,
        }
    
    def _convert_subtitle_result(self, result: SubtitleGenerationResult) -> Dict[str, Any]:
        """Convert SubtitleGenerationResult to dictionary."""
        return {
            'status': result.status,
            'assets_created': result.assets_created,
            'shots_processed': result.shots_processed,
            'errors': result.errors,
            'execution_time_ms': result.execution_time_ms,
            'metrics': result.metrics,
        }
    
    def _convert_tts_result(self, result: TTSStageResult) -> Dict[str, Any]:
        """Convert TTSStageResult to dictionary."""
        return {
            'status': result.status,
            'assets_created': result.assets_created,
            'shots_processed': result.shots_processed,
            'shots_failed': result.shots_failed,
            'errors': result.errors,
            'execution_time_ms': result.execution_time_ms,
            'metrics': result.metrics,
        }
    
    def _convert_preview_result(self, result: PreviewExportResult) -> Dict[str, Any]:
        """Convert PreviewExportResult to dictionary."""
        return {
            'status': result.status,
            'assets_created': result.assets_created,
            'shots_processed': result.shots_collected,
            'shots_failed': 0,  # Preview export doesn't track per-shot failures
            'errors': result.errors,
            'execution_time_ms': result.execution_time_ms,
            'metrics': result.metrics,
        }
    
    def _convert_qa_result(self, result) -> Dict[str, Any]:
        """Convert QAStageResult to dictionary."""
        return {
            'status': result.status,
            'assets_created': 0,  # QA doesn't create assets
            'shots_processed': 0,
            'shots_failed': 0,
            'errors': result.errors,
            'execution_time_ms': result.execution_time_ms,
            'metrics': {
                'should_block': result.should_block,
                'checks_executed': len(result.qa_results),
            },
        }
    
    def _should_continue_after_failure(
        self,
        stage_type: str,
        result: Dict[str, Any],
    ) -> bool:
        """
        Decide whether to continue executing subsequent stages after a failure.
        
        Implements Requirement 10.3
        
        Args:
            stage_type: Type of stage that failed
            result: Stage execution result
            
        Returns:
            True if should continue, False otherwise
        """
        status = result.get('status', 'failed')
        
        # Continue if partial success (some assets were created)
        if status == 'partial_success':
            return True
        
        # For QA stage, check if it should block (Iteration 5)
        if stage_type == 'qa':
            should_block = result.get('metrics', {}).get('should_block', False)
            return not should_block
        
        # For critical stages, stop on complete failure
        critical_stages = ['image_render']
        if stage_type in critical_stages and status == 'failed':
            return False
        
        # For non-critical stages, continue even on failure
        # (e.g., subtitle or TTS failure shouldn't block preview generation)
        return True
    
    def _update_stage_task_metrics(
        self,
        stage_task_id: UUID,
        result: Dict[str, Any],
    ) -> None:
        """
        Update StageTask with execution metrics and final status.
        
        Implements Requirement 10.5
        
        Args:
            stage_task_id: StageTask ID
            result: Stage execution result with metrics
        """
        # Extract metrics from result
        metrics = result.get('metrics', {})
        
        # Add high-level metrics from result
        metrics['execution_time_ms'] = result.get('execution_time_ms', 0)
        metrics['assets_created'] = result.get('assets_created', 0)
        metrics['shots_processed'] = result.get('shots_processed', 0)
        metrics['shots_failed'] = result.get('shots_failed', 0)
        
        # Determine final status
        status = result.get('status', 'failed')
        task_status_map = {
            'succeeded': 'succeeded',
            'partial_success': 'succeeded',
            'failed': 'failed',
        }
        final_status = task_status_map.get(status, 'failed')
        
        # Update stage task with metrics and status
        self.stage_task_repo.update_metrics(
            stage_task_id,
            metrics=metrics,
            commit=False,
        )
        
        # Update status and finished_at
        error_message = None
        if result.get('errors'):
            error_message = "; ".join(result['errors'][:3])  # Store first 3 errors
        
        self.stage_task_repo.update_status(
            stage_task_id,
            final_status,
            finished_at=datetime.utcnow(),
            error_message=error_message,
            commit=True,
        )
    
    def _determine_final_status(
        self,
        stages_completed: List[str],
        stages_failed: List[str],
        total_stages: int,
    ) -> str:
        """
        Determine the final workflow status based on stage results.
        
        Implements Requirement 10.4
        
        Args:
            stages_completed: List of completed stage types
            stages_failed: List of failed stage types
            total_stages: Total number of stages to execute
            
        Returns:
            Final status string
        """
        if not stages_failed:
            return "media_ready"
        elif stages_completed:
            return "media_partial"
        else:
            return "media_failed"
    
    def _update_workflow_status(
        self,
        workflow_run_id: UUID,
        status: str,
        errors: List[str],
    ) -> None:
        """
        Update WorkflowRun status and failure information.
        
        Implements Requirement 10.4
        
        Args:
            workflow_run_id: WorkflowRun ID
            status: Final status
            errors: List of error messages
        """
        failure_reason = None
        if errors:
            failure_reason = "; ".join(errors[:3])  # Store first 3 errors
        
        self.workflow_repo.update_status(
            workflow_run_id,
            status=status,
            failure_reason=failure_reason,
            commit=True,
        )
