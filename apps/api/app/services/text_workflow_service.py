from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.document_repository import DocumentRepository
from app.repositories.episode_repository import EpisodeRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.repositories.workflow_repository import WorkflowRepository

TEXT_STAGE_SEQUENCE = ["brief", "story_bible", "character", "script", "storyboard"]

_STAGE_DOCUMENTS = {
    "brief": {
        "document_type": "brief",
        "status": "pending",
        "title": "EP{episode_no:02d} Brief",
    },
    "story_bible": {
        "document_type": "story_bible",
        "status": "ready",
        "title": "EP{episode_no:02d} Story Bible",
    },
    "character": {
        "document_type": "character_profile",
        "status": "ready",
        "title": "EP{episode_no:02d} Character Profile",
    },
    "script": {
        "document_type": "script_draft",
        "status": "ready",
        "title": "EP{episode_no:02d} Script Draft",
    },
    "storyboard": {
        "document_type": "visual_spec",
        "status": "ready",
        "title": "EP{episode_no:02d} Storyboard Visual Spec",
    },
}


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

    def execute_text_chain(self, project, episode, workflow, start_stage: str) -> dict[str, str]:
        if start_stage not in TEXT_STAGE_SEQUENCE:
            raise ValueError(f"Unsupported text start stage: {start_stage}")

        start_index = TEXT_STAGE_SEQUENCE.index(start_stage)
        stage_sequence = TEXT_STAGE_SEQUENCE[start_index:]
        now = datetime.now(timezone.utc)
        latest_document_refs: list[dict[str, str]] = []
        script_version = episode.script_version
        storyboard_version = episode.storyboard_version

        for stage_type in stage_sequence:
            stage_task = self.stage_tasks.create(
                commit=False,
                workflow_run_id=workflow.id,
                project_id=project.id,
                episode_id=episode.id,
                stage_type=stage_type,
                task_status="succeeded",
                agent_name=f"{stage_type.replace('_', ' ').title()} Agent",
                worker_kind="agent",
                input_ref_jsonb=list(latest_document_refs),
                output_ref_jsonb=[],
                review_required=stage_type in {"brief", "storyboard"},
                review_status="pending" if stage_type in {"brief", "storyboard"} else None,
                started_at=now,
                finished_at=now,
            )

            if stage_type == "storyboard":
                visual_document = self._create_stage_document(project, episode, stage_task, stage_type)
                storyboard_version = self._create_storyboard_outputs(project, episode, stage_task, visual_document)
                latest_document_refs = [{"ref_type": "document", "ref_id": str(visual_document.id)}]
            else:
                document = self._create_stage_document(project, episode, stage_task, stage_type)
                latest_document_refs = [{"ref_type": "document", "ref_id": str(document.id)}]
                if stage_type == "script":
                    script_version = document.version

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

    def _create_stage_document(self, project, episode, stage_task, stage_type: str):
        config = _STAGE_DOCUMENTS[stage_type]
        version = self.documents.latest_version_for_episode_and_type(episode.id, config["document_type"]) + 1
        document = self.documents.create(
            commit=False,
            project_id=project.id,
            episode_id=episode.id,
            stage_task_id=stage_task.id,
            document_type=config["document_type"],
            version=version,
            status=config["status"],
            title=config["title"].format(episode_no=episode.episode_no),
            content_jsonb=self._build_document_payload(project, episode, stage_type, version),
            summary_text=self._build_document_summary(project, episode, stage_type),
            created_by=None,
        )
        stage_task.output_ref_jsonb = [{"ref_type": "document", "ref_id": str(document.id)}]
        return document

    def _create_storyboard_outputs(self, project, episode, stage_task, visual_document) -> int:
        shot_version = self.shots.latest_version_for_episode(episode.id) + 1
        shot_payloads = []
        for shot_no, payload in enumerate(self._build_storyboard_shots(), start=1):
            shot_payloads.append(
                {
                    "project_id": project.id,
                    "episode_id": episode.id,
                    "stage_task_id": stage_task.id,
                    "scene_no": 1,
                    "shot_no": shot_no,
                    "shot_code": f"SHOT_{shot_no:02d}",
                    "status": payload["status"],
                    "duration_ms": payload["duration_ms"],
                    "camera_size": payload["camera_size"],
                    "camera_angle": payload["camera_angle"],
                    "movement_type": payload["movement_type"],
                    "characters_jsonb": payload["characters_jsonb"],
                    "action_text": payload["action_text"],
                    "dialogue_text": payload["dialogue_text"],
                    "visual_constraints_jsonb": payload["visual_constraints_jsonb"],
                    "version": shot_version,
                }
            )
        shots = self.shots.create_many(shot_payloads, commit=False)
        stage_task.output_ref_jsonb = [
            {"ref_type": "document", "ref_id": str(visual_document.id)},
            *[{"ref_type": "shot", "ref_id": str(shot.id)} for shot in shots],
        ]
        return shot_version

    def _build_document_payload(self, project, episode, stage_type: str, version: int) -> dict:
        base = {
            "project_name": project.name,
            "episode_title": episode.title,
            "version": version,
            "stage_type": stage_type,
        }
        payloads = {
            "brief": {
                "hook": f"{episode.title or 'Episode'} builds around a public identity reversal.",
                "target_duration_sec": episode.target_duration_sec,
                "platform": getattr(project, "target_platform", "douyin"),
                "audience": getattr(project, "target_audience", None),
            },
            "story_bible": {
                "world_rules": ["Keep the family pressure visible", "Use the red earring as a visual anchor"],
                "core_conflict": "The lead is publicly challenged before turning the power dynamic around.",
            },
            "character": {
                "characters": [
                    {"name": "Lead", "trait": "restrained but sharp"},
                    {"name": "Antagonist", "trait": "dominating and verbally aggressive"},
                ]
            },
            "script": {
                "beats": [
                    "The lead is questioned in public",
                    "The antagonist presses harder",
                    "A family token flips the scene",
                ]
            },
            "storyboard": {
                "palette": "cold white + deep red",
                "camera_rule": "favor close-ups and pressure angles",
                "anchor": "red earring + family pendant",
            },
        }
        base.update(payloads[stage_type])
        return base

    def _build_document_summary(self, project, episode, stage_type: str) -> str:
        summaries = {
            "brief": f"Generated a first-pass brief for {episode.title or 'the episode'} with an identity-reversal hook.",
            "story_bible": "Captured the world rules, tone and conflict anchors for the episode.",
            "character": "Created the core character notes that the script and storyboard can reuse.",
            "script": "Built a three-beat script draft with a cliffhanger ending.",
            "storyboard": "Turned the script into a shot list and visual constraints, now waiting for review.",
        }
        return summaries[stage_type]

    def _build_storyboard_shots(self) -> list[dict]:
        return [
            {
                "status": "ready",
                "duration_ms": 6000,
                "camera_size": "close_up",
                "camera_angle": "eye_level",
                "movement_type": "push_in",
                "characters_jsonb": ["Lead"],
                "action_text": "The lead lifts her chin as the red earring becomes the visual anchor.",
                "dialogue_text": "You still think I was abandoned?",
                "visual_constraints_jsonb": {
                    "lighting": "cold white key light",
                    "anchor": "red earring",
                    "wardrobe": "plain white dress",
                },
            },
            {
                "status": "ready",
                "duration_ms": 5000,
                "camera_size": "medium",
                "camera_angle": "low_angle",
                "movement_type": "static",
                "characters_jsonb": ["Antagonist", "Lead"],
                "action_text": "The antagonist steps forward and compresses the space.",
                "dialogue_text": "You do not get to claim that name.",
                "visual_constraints_jsonb": {
                    "blocking": "antagonist pushes in",
                    "background": "ancestral hall screen",
                    "emotion": "pressure",
                },
            },
            {
                "status": "warning",
                "duration_ms": 7000,
                "camera_size": "close_up",
                "camera_angle": "high_angle",
                "movement_type": "tilt_down",
                "characters_jsonb": ["Lead", "Elder"],
                "action_text": "The family pendant drops into frame and the elder freezes.",
                "dialogue_text": "Now tell me again that I do not belong here.",
                "visual_constraints_jsonb": {
                    "prop": "family pendant",
                    "timing_risk": "pause may run long",
                    "anchor": "earring + pendant",
                },
            },
        ]
