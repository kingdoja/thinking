from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.project import EpisodeResponse, ProjectResponse
from app.schemas.workflow import WorkflowRunResponse

DocumentStatus = Literal["draft", "approved", "archived", "ready", "pending"]
AssetType = Literal[
    "character_reference",
    "scene_reference",
    "shot_image",
    "audio_voice",
    "subtitle_file",
    "preview_video",
    "final_video",
    "cover_image",
    "export_bundle",
]
QAResult = Literal["pass", "fail", "warn", "pending"]
StageTaskStatus = Literal["pending", "running", "succeeded", "failed", "skipped", "blocked"]
ReviewDecisionType = Literal["approved", "rejected", "request_changes"]
ReviewSummaryStatus = Literal["none", "pending", "approved", "rejected", "request_changes"]


class DocumentSummaryResponse(BaseModel):
    id: UUID
    document_type: str
    version: int
    status: DocumentStatus
    title: Optional[str] = None
    summary_text: Optional[str] = None
    updated_at: Optional[datetime] = None


class AssetSummaryResponse(BaseModel):
    id: UUID
    asset_type: AssetType
    storage_key: str
    mime_type: str
    size_bytes: int
    duration_ms: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_selected: bool = False
    version: int = 1
    created_at: Optional[datetime] = None


class StageTaskSummaryResponse(BaseModel):
    id: UUID
    stage_type: str
    task_status: StageTaskStatus
    worker_kind: str
    review_required: bool = False
    review_status: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ShotSummaryResponse(BaseModel):
    id: Optional[UUID] = None
    code: str
    shot_index: Optional[int] = None
    scene_no: Optional[int] = None
    shot_no: Optional[int] = None
    title: Optional[str] = None
    duration_ms: int
    status: str
    camera_size: Optional[str] = None
    camera_angle: Optional[str] = None
    movement_type: Optional[str] = None
    characters: List[str] = Field(default_factory=list)
    visual_constraints_summary: Optional[Dict[str, Any]] = None
    visual_spec_doc_id: Optional[UUID] = None
    stage_task_id: Optional[UUID] = None
    version: int = 1
    updated_at: Optional[datetime] = None


class SubmitReviewDecisionRequest(BaseModel):
    stage_task_id: UUID
    decision: ReviewDecisionType
    decision_note: Optional[str] = Field(default=None, max_length=1000)


class ReviewDecisionSummaryResponse(BaseModel):
    id: UUID
    status: ReviewDecisionType
    decision_note: Optional[str] = None
    stage_task_id: UUID
    created_at: Optional[datetime] = None


class QAReportSummaryResponse(BaseModel):
    id: UUID
    qa_type: str
    result: QAResult
    severity: str
    issue_count: int
    rerun_stage_type: Optional[str] = None
    created_at: Optional[datetime] = None


class WorkspaceQAResponse(BaseModel):
    result: QAResult
    issue_count: int
    reports: List[QAReportSummaryResponse] = Field(default_factory=list)


class WorkspaceReviewResponse(BaseModel):
    status: ReviewSummaryStatus = "none"
    pending_count: int = 0
    latest_decision: Optional[ReviewDecisionSummaryResponse] = None


class EpisodeWorkspaceResponse(BaseModel):
    project: ProjectResponse
    episode: EpisodeResponse
    documents: List[DocumentSummaryResponse] = Field(default_factory=list)
    stage_tasks: List[StageTaskSummaryResponse] = Field(default_factory=list)
    shots: List[ShotSummaryResponse] = Field(default_factory=list)
    assets: List[AssetSummaryResponse] = Field(default_factory=list)
    qa_summary: WorkspaceQAResponse
    review_summary: WorkspaceReviewResponse = Field(default_factory=WorkspaceReviewResponse)
    latest_workflow: Optional[WorkflowRunResponse] = None
    generated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
