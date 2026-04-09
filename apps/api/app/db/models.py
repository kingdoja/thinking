from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    source_mode: Mapped[str] = mapped_column(String(32))
    genre: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_platform: Mapped[str] = mapped_column(String(32))
    target_audience: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    brief_version: Mapped[int] = mapped_column(Integer, default=0)
    current_episode_no: Mapped[int] = mapped_column(Integer, default=1)
    cover_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EpisodeModel(Base):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    current_stage: Mapped[str] = mapped_column(String(32), default="brief")
    target_duration_sec: Mapped[int] = mapped_column(Integer)
    script_version: Mapped[int] = mapped_column(Integer, default=0)
    storyboard_version: Mapped[int] = mapped_column(Integer, default=0)
    visual_version: Mapped[int] = mapped_column(Integer, default=0)
    audio_version: Mapped[int] = mapped_column(Integer, default=0)
    export_version: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"))
    workflow_kind: Mapped[str] = mapped_column(String(32))
    temporal_workflow_id: Mapped[str] = mapped_column(String(128), unique=True)
    temporal_run_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    started_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    rerun_from_stage: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StageTaskModel(Base):
    __tablename__ = "stage_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"))
    stage_type: Mapped[str] = mapped_column(String(32))
    task_status: Mapped[str] = mapped_column(String(32), default="pending")
    agent_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    worker_kind: Mapped[str] = mapped_column(String(32))
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    input_ref_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    output_ref_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True)
    stage_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stage_tasks.id", ondelete="SET NULL"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    content_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ShotModel(Base):
    __tablename__ = "shots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"))
    stage_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stage_tasks.id", ondelete="SET NULL"), nullable=True)
    scene_no: Mapped[int] = mapped_column(Integer)
    shot_no: Mapped[int] = mapped_column(Integer)
    shot_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    duration_ms: Mapped[int] = mapped_column(Integer)
    camera_size: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    camera_angle: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    movement_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    characters_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    action_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dialogue_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_constraints_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssetModel(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True)
    stage_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stage_tasks.id", ondelete="SET NULL"), nullable=True)
    shot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("shots.id", ondelete="SET NULL"), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    metadata_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QAReportModel(Base):
    __tablename__ = "qa_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"))
    stage_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stage_tasks.id", ondelete="SET NULL"), nullable=True)
    qa_type: Mapped[str] = mapped_column(String(32))
    target_ref_type: Mapped[str] = mapped_column(String(32))
    target_ref_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    result: Mapped[str] = mapped_column(String(16))
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    severity: Mapped[str] = mapped_column(String(16))
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    issues_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    rerun_stage_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewDecisionModel(Base):
    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"))
    stage_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stage_tasks.id", ondelete="CASCADE"))
    reviewer_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    decision: Mapped[str] = mapped_column(String(16))
    comment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
