from datetime import datetime, timezone
from typing import Dict, List
import sys
from pathlib import Path
from uuid import UUID
import logging

from sqlalchemy.orm import Session

from app.repositories.document_repository import DocumentRepository
from app.repositories.episode_repository import EpisodeRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.repositories.workflow_repository import WorkflowRepository

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add agent runtime to path
agent_runtime_path = Path(__file__).parent.parent.parent.parent.parent / "workers" / "agent-runtime"
if str(agent_runtime_path) not in sys.path:
    sys.path.insert(0, str(agent_runtime_path))

from agents.base_agent import StageTaskInput, StageTaskOutput, DocumentRef, LockedRef
from agents.brief_agent import BriefAgent
from agents.story_bible_agent import StoryBibleAgent
from agents.character_agent import CharacterAgent
from agents.script_agent import ScriptAgent
from agents.storyboard_agent import StoryboardAgent
from services.mock_llm_service import MockLLMService
from services.validator import Validator

TEXT_STAGE_SEQUENCE = ["brief", "story_bible", "character", "script", "storyboard"]


class TextWorkflowService:
    def __init__(
        self,
        db: Session,
        stage_tasks: StageTaskRepository,
        documents: DocumentRepository,
        shots: ShotRepository,
        episodes: EpisodeRepository,
        workflows: WorkflowRepository,
    ) -> None:
        self.db = db
        self.stage_tasks = stage_tasks
        self.documents = documents
        self.shots = shots
        self.episodes = episodes
        self.workflows = workflows
        
        # Initialize LLM service and validator
        self.llm_service = MockLLMService()
        self.validator = Validator()
        
        # Initialize agents
        self.agents = {
            "brief": BriefAgent(db_session=db, llm_service=self.llm_service, validator=self.validator),
            "story_bible": StoryBibleAgent(db_session=db, llm_service=self.llm_service, validator=self.validator),
            "character": CharacterAgent(db_session=db, llm_service=self.llm_service, validator=self.validator),
            "script": ScriptAgent(db_session=db, llm_service=self.llm_service, validator=self.validator),
            "storyboard": StoryboardAgent(db_session=db, llm_service=self.llm_service, validator=self.validator),
        }

    def execute_text_chain(self, project, episode, workflow, start_stage: str) -> Dict[str, str]:
        """
        Execute the text chain workflow using real agents.
        
        Implements Requirements:
        - 1.2: Execute stages in order
        - 1.5: Preserve intermediate artifacts on failure
        - 11.1: Build StageTaskInput for each stage
        - 11.2: Handle StageTaskOutput
        - 11.3: Decide next step based on output status
        - 12.1, 12.2, 12.3: Log execution metrics
        """
        if start_stage not in TEXT_STAGE_SEQUENCE:
            raise ValueError(f"Unsupported text start stage: {start_stage}")

        logger.info(f"Starting text chain workflow for episode {episode.id}, starting from stage: {start_stage}")
        
        start_index = TEXT_STAGE_SEQUENCE.index(start_stage)
        stage_sequence = TEXT_STAGE_SEQUENCE[start_index:]
        now = datetime.now(timezone.utc)
        latest_document_refs: List[Dict[str, str]] = []
        script_version = episode.script_version
        storyboard_version = episode.storyboard_version

        for stage_type in stage_sequence:
            # Requirement 12.1: Log stage start
            logger.info(f"Starting stage: {stage_type} for episode {episode.id}")
            
            # Create stage task record
            stage_task = self.stage_tasks.create(
                commit=False,
                workflow_run_id=workflow.id,
                project_id=project.id,
                episode_id=episode.id,
                stage_type=stage_type,
                task_status="running",
                agent_name=f"{stage_type.replace('_', ' ').title()} Agent",
                worker_kind="agent_runtime",
                input_ref_jsonb=list(latest_document_refs),
                output_ref_jsonb=[],
                review_required=stage_type in {"brief", "storyboard"},
                review_status="pending" if stage_type in {"brief", "storyboard"} else None,
                started_at=now,
                finished_at=None,
                attempt_no=1,
                max_retries=3,
            )
            self.db.flush()
            
            # Log stage task creation (Requirement 12.1)
            logger.info(
                f"Stage task created - stage_type: {stage_type}, "
                f"started_at: {now.isoformat()}, "
                f"attempt_no: 1, "
                f"stage_task_id: {stage_task.id}"
            )
            
            # Execute agent with retry logic (Requirement 11.4)
            output = self._execute_stage_with_retry(stage_task, stage_type, episode, project)
            
            # Update stage task with output
            stage_task.task_status = output.status
            stage_task.finished_at = datetime.now(timezone.utc)
            stage_task.output_ref_jsonb = [
                {"ref_type": ref.ref_type, "ref_id": ref.ref_id}
                for ref in (output.document_refs + output.asset_refs)
            ]
            
            # Requirement 12.2: Log stage completion
            duration_ms = output.metrics.get("duration_ms", 0)
            token_usage = output.metrics.get("token_usage", 0)
            logger.info(
                f"Stage completed - stage_type: {stage_type}, "
                f"status: {output.status}, "
                f"finished_at: {stage_task.finished_at.isoformat()}, "
                f"duration_ms: {duration_ms}, "
                f"token_usage: {token_usage}"
            )
            
            if output.status == "failed":
                # Requirement 1.5: Preserve intermediate artifacts on failure
                # Requirement 2.5, 3.5, 4.5, 5.5: Record error information
                # Requirement 12.3: Log failure
                stage_task.error_code = output.error_code
                stage_task.error_message = output.error_message
                logger.error(
                    f"Stage failed - stage_type: {stage_type}, "
                    f"error_code: {output.error_code}, "
                    f"error_message: {output.error_message}"
                )
                self.workflows.update_status(workflow.id, "failed", commit=False)
                workflow.status = "failed"
                self.db.commit()
                return {"workflow_status": workflow.status, "error": output.error_message}
            
            # Requirement 12.5: Log document commits
            for doc_ref in output.document_refs:
                logger.info(
                    f"Document committed - document_type: {doc_ref.document_type}, "
                    f"document_id: {doc_ref.ref_id}, "
                    f"version: {doc_ref.version}, "
                    f"created_by: None (AI-generated)"
                )
            
            # Update stage task with document refs
            if stage_type == "storyboard":
                # Update storyboard version from shots
                if output.asset_refs:
                    storyboard_version = self._get_shot_version_from_refs(output.asset_refs)
            elif stage_type == "script":
                # Update script version from document
                if output.document_refs:
                    script_version = output.document_refs[0].version
            
            # Prepare refs for next stage (Requirement 11.3)
            latest_document_refs = [
                {"ref_type": ref.ref_type, "ref_id": ref.ref_id}
                for ref in output.document_refs
            ]

        logger.info(f"Text chain workflow completed successfully for episode {episode.id}")
        
        self.workflows.update_status(workflow.id, "waiting_review", commit=False)
        workflow.status = "waiting_review"
        self.episodes.update_progress(
            episode.id,
            commit=False,
            current_stage="storyboard",
            status="storyboard_ready",
            script_version=script_version,
            storyboard_version=storyboard_version,
        )
        self.db.commit()
        self.db.refresh(workflow)
        return {"workflow_status": workflow.status}
    
    def _build_stage_input(
        self,
        workflow_run_id: UUID,
        project_id: UUID,
        episode_id: UUID,
        stage_type: str,
        input_refs: List[Dict[str, str]],
        episode,
        project
    ) -> StageTaskInput:
        """
        Build StageTaskInput for a stage.
        
        Implements Requirement 11.1: Workflow构造StageTaskInput
        """
        # Convert dict refs to DocumentRef objects
        doc_refs = [
            DocumentRef(
                ref_type=ref["ref_type"],
                ref_id=ref["ref_id"]
            )
            for ref in input_refs
        ]
        
        # Build constraints based on stage type
        constraints = {}
        if stage_type == "brief":
            constraints = {
                "raw_material": getattr(episode, "source_material", "Sample novel excerpt for testing"),
                "platform": getattr(project, "target_platform", "douyin"),
                "target_duration_sec": episode.target_duration_sec,
                "target_audience": getattr(project, "target_audience", "General audience")
            }
        elif stage_type == "storyboard":
            constraints = {
                "platform": getattr(project, "target_platform", "douyin"),
                "target_duration_sec": episode.target_duration_sec,
                "aspect_ratio": "9:16",
                "max_shots": 10
            }
        
        return StageTaskInput(
            workflow_run_id=workflow_run_id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type=stage_type,
            input_refs=doc_refs,
            locked_refs=[],  # TODO: Implement locked refs tracking
            constraints=constraints,
            target_ref_ids=[],
            raw_material=constraints.get("raw_material")
        )
    
    def _get_shot_version_from_refs(self, asset_refs: list) -> int:
        """Get shot version from asset refs."""
        if not asset_refs:
            return 1
        
        # Get the first shot ref and query its version
        shot_ref = next((ref for ref in asset_refs if ref.ref_type == "shot"), None)
        if shot_ref:
            from app.db.models import ShotModel
            shot = self.db.query(ShotModel).filter(ShotModel.id == UUID(shot_ref.ref_id)).first()
            if shot:
                return shot.version
        
        return 1
    
    def _execute_stage_with_retry(self, stage_task, stage_type: str, episode, project) -> StageTaskOutput:
        """
        Execute a stage with retry logic.
        
        Implements Requirements:
        - 1.5: Preserve intermediate artifacts on failure
        - 2.5, 3.5, 4.5, 5.5: Record error information
        - 11.4: Workflow controls retry logic
        - 12.1, 12.2, 12.3: Log execution metrics
        """
        max_attempts = stage_task.max_retries
        last_output = None
        
        for attempt in range(1, max_attempts + 1):
            stage_task.attempt_no = attempt
            self.db.flush()
            
            # Requirement 12.1: Log attempt start
            logger.info(f"Stage {stage_type} attempt {attempt}/{max_attempts} starting")
            
            try:
                # Build StageTaskInput (Requirement 11.1)
                task_input = self._build_stage_input(
                    workflow_run_id=stage_task.workflow_run_id,
                    project_id=stage_task.project_id,
                    episode_id=stage_task.episode_id,
                    stage_type=stage_type,
                    input_refs=stage_task.input_ref_jsonb,
                    episode=episode,
                    project=project
                )
                
                # Execute agent (Requirement 11.2)
                agent = self.agents[stage_type]
                output = agent.execute(task_input)
                
                # If succeeded, return immediately
                if output.status == "succeeded":
                    logger.info(f"Stage {stage_type} attempt {attempt} succeeded")
                    return output
                
                # If failed, store output and retry if attempts remain
                last_output = output
                
                # Requirement 12.3: Log failure
                logger.warning(
                    f"Stage {stage_type} attempt {attempt} failed - "
                    f"error_code: {output.error_code}, "
                    f"error_message: {output.error_message}"
                )
                
                if attempt < max_attempts:
                    logger.info(f"Retrying stage {stage_type}...")
                    continue
                else:
                    # Max retries reached
                    logger.error(f"Stage {stage_type} failed after {max_attempts} attempts")
                    return output
                    
            except Exception as e:
                # Unexpected exception during execution
                # Requirement 12.3: Log exception
                logger.exception(f"Stage {stage_type} attempt {attempt} raised exception: {str(e)}")
                
                last_output = StageTaskOutput(
                    status="failed",
                    document_refs=[],
                    asset_refs=[],
                    warnings=[],
                    quality_notes=[],
                    metrics={},
                    error_code="EXECUTION_EXCEPTION",
                    error_message=f"Unexpected error during stage execution: {str(e)}"
                )
                
                if attempt < max_attempts:
                    logger.info(f"Retrying stage {stage_type} after exception...")
                    continue
                else:
                    logger.error(f"Stage {stage_type} failed with exception after {max_attempts} attempts")
                    return last_output
        
        # Should not reach here, but return last output as fallback
        return last_output or StageTaskOutput(
            status="failed",
            document_refs=[],
            asset_refs=[],
            warnings=[],
            quality_notes=[],
            metrics={},
            error_code="UNKNOWN_ERROR",
            error_message="Stage execution failed with unknown error"
        )
