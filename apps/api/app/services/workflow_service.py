from typing import Dict

from sqlalchemy.orm import Session

from app.db.models import EpisodeModel, ProjectModel
from app.repositories.document_repository import DocumentRepository
from app.repositories.episode_repository import EpisodeRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.schemas.workflow import StartEpisodeWorkflowRequest
from app.services.text_workflow_service import TEXT_STAGE_SEQUENCE, TextWorkflowService
from app.services.media_workflow_service import MEDIA_STAGE_SEQUENCE, MediaWorkflowService

STAGE_WORKER_KIND: Dict[str, str] = {
    "brief": "agent",
    "story_bible": "agent",
    "character": "agent",
    "script": "agent",
    "storyboard": "agent",
    "visual_spec": "agent",
    "image_render": "media",
    "subtitle": "agent",
    "tts": "media",
    "edit_export_preview": "media",
    "qa": "qa",
    "human_review_gate": "system",
    "export_final": "media",
}

STAGE_AGENT_NAME: Dict[str, str] = {
    "brief": "Brief Agent",
    "story_bible": "Story Bible Agent",
    "character": "Character Agent",
    "script": "Script Agent",
    "storyboard": "Storyboard Agent",
    "visual_spec": "Storyboard Agent",
    "subtitle": "Subtitle Agent",
    "qa": "QA Agent",
}

REVIEW_REQUIRED_STAGES = {"brief", "storyboard", "qa"}


class WorkflowService:
    def __init__(
        self,
        db: Session,
        workflows: WorkflowRepository,
        stage_tasks: StageTaskRepository,
        documents: DocumentRepository,
        shots: ShotRepository,
        episodes: EpisodeRepository,
        media_workflow: MediaWorkflowService = None,
    ) -> None:
        self.db = db
        self.workflows = workflows
        self.stage_tasks = stage_tasks
        self.text_workflow = TextWorkflowService(db, stage_tasks, documents, shots, episodes, workflows)
        self.media_workflow = media_workflow

    def start_episode_workflow(self, project_id, episode_id, payload: StartEpisodeWorkflowRequest):
        workflow = self.workflows.create(
            project_id=project_id,
            episode_id=episode_id,
            payload=payload,
            workflow_kind="episode",
            commit=False,
        )

        if payload.start_stage in TEXT_STAGE_SEQUENCE:
            project = self.db.get(ProjectModel, project_id)
            episode = self.db.get(EpisodeModel, episode_id)
            if project is None or episode is None:
                raise LookupError("Workspace not found")

            self.text_workflow.execute_text_chain(project, episode, workflow, payload.start_stage)
            self.db.refresh(workflow)
            return workflow
        
        # Check if this is a media stage
        if payload.start_stage in MEDIA_STAGE_SEQUENCE and self.media_workflow:
            project = self.db.get(ProjectModel, project_id)
            episode = self.db.get(EpisodeModel, episode_id)
            if project is None or episode is None:
                raise LookupError("Workspace not found")
            
            # Execute media workflow asynchronously
            # Note: This requires the caller to handle async execution
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self.media_workflow.execute_media_chain(project, episode, workflow, payload.start_stage)
            )
            
            self.db.refresh(workflow)
            return workflow

        self.stage_tasks.create(
            commit=False,
            workflow_run_id=workflow.id,
            project_id=project_id,
            episode_id=episode_id,
            stage_type=payload.start_stage,
            task_status="pending",
            agent_name=STAGE_AGENT_NAME.get(payload.start_stage),
            worker_kind=STAGE_WORKER_KIND[payload.start_stage],
            input_ref_jsonb=[],
            output_ref_jsonb=[],
            review_required=payload.start_stage in REVIEW_REQUIRED_STAGES,
            review_status=None,
            started_at=None,
        )

        self.db.commit()
        self.db.refresh(workflow)
        return workflow
