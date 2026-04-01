from datetime import datetime
from typing import Any, Literal
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
    title: str | None = None
    summary_text: str | None = None
    updated_at: datetime | None = None


class AssetSummaryResponse(BaseModel):
    id: UUID
    asset_type: AssetType
    storage_key: str
    mime_type: str
    size_bytes: int
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    is_selected: bool = False
    version: int = 1
    created_at: datetime | None = None


class StageTaskSummaryResponse(BaseModel):
    id: UUID
    stage_type: str
    task_status: StageTaskStatus
    worker_kind: str
    review_required: bool = False
    review_status: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


class ShotSummaryResponse(BaseModel):
    id: UUID | None = None
    code: str
    shot_index: int | None = None
    title: str | None = None
    duration_ms: int
    status: str
    stage_task_id: UUID | None = None
    updated_at: datetime | None = None


class SubmitReviewDecisionRequest(BaseModel):
    stage_task_id: UUID
    decision: ReviewDecisionType
    decision_note: str | None = Field(default=None, max_length=1000)


class ReviewDecisionSummaryResponse(BaseModel):
    id: UUID
    status: ReviewDecisionType
    decision_note: str | None = None
    stage_task_id: UUID
    created_at: datetime | None = None


class QAReportSummaryResponse(BaseModel):
    id: UUID
    qa_type: str
    result: QAResult
    severity: str
    issue_count: int
    rerun_stage_type: str | None = None
    created_at: datetime | None = None


class WorkspaceQAResponse(BaseModel):
    result: QAResult
    issue_count: int
    reports: list[QAReportSummaryResponse] = Field(default_factory=list)


class WorkspaceReviewResponse(BaseModel):
    status: ReviewSummaryStatus = "none"
    pending_count: int = 0
    latest_decision: ReviewDecisionSummaryResponse | None = None


class EpisodeWorkspaceResponse(BaseModel):
    project: ProjectResponse
    episode: EpisodeResponse
    documents: list[DocumentSummaryResponse] = Field(default_factory=list)
    stage_tasks: list[StageTaskSummaryResponse] = Field(default_factory=list)
    shots: list[ShotSummaryResponse] = Field(default_factory=list)
    assets: list[AssetSummaryResponse] = Field(default_factory=list)
    qa_summary: WorkspaceQAResponse
    review_summary: WorkspaceReviewResponse = Field(default_factory=WorkspaceReviewResponse)
    latest_workflow: WorkflowRunResponse | None = None
    generated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
