"""
Provider Call Monitor

Records every Provider call with timing, success/failure status, and request_id.
Also computes cost estimates for Image and TTS providers, and aggregates
performance metrics at Stage, Episode, and Project levels.

Implements Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EpisodeModel, StageTaskModel


# ---------------------------------------------------------------------------
# Cost rate constants (placeholder rates — swap for real pricing)
# ---------------------------------------------------------------------------

# Image generation: cost per successful call (USD)
IMAGE_COST_PER_CALL: float = 0.05

# TTS: cost per 1 000 characters (USD)
TTS_COST_PER_1K_CHARS: float = 0.016


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ProviderCallRecord:
    """
    Immutable record of a single Provider API call.

    Attributes:
        provider_name: e.g. 'stable_diffusion', 'azure_tts'
        operation: e.g. 'generate_image', 'synthesize_speech'
        started_at: UTC timestamp when the call started
        duration_ms: Wall-clock time of the call in milliseconds
        success: Whether the call returned a successful result
        request_id: Provider-supplied request / trace ID (if any)
        error: Error message when success=False
        extra: Provider-specific metadata (model, chars, etc.)
    """

    provider_name: str
    operation: str
    started_at: datetime
    duration_ms: int
    success: bool
    request_id: Optional[str] = None
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostEstimate:
    """
    Estimated monetary cost for a set of Provider calls.

    Attributes:
        image_calls: Number of image generation calls
        image_cost_usd: Estimated cost for image calls
        tts_characters: Total characters synthesized
        tts_cost_usd: Estimated cost for TTS calls
        total_cost_usd: Sum of all costs
    """

    image_calls: int = 0
    image_cost_usd: float = 0.0
    tts_characters: int = 0
    tts_cost_usd: float = 0.0
    total_cost_usd: float = 0.0


@dataclass
class StageMetrics:
    """
    Aggregated performance metrics for a single Stage execution.

    Attributes:
        stage_type: e.g. 'image_render', 'tts'
        stage_task_id: UUID of the StageTask record
        duration_ms: Total wall-clock time of the stage
        provider_calls: Total Provider API calls made
        success_count: Successful Provider calls
        failure_count: Failed Provider calls
        retry_count: Total retry attempts across all calls
        assets_created: Number of Asset records created
        shots_processed: Shots that produced at least one asset
        shots_failed: Shots that produced no asset
        estimated_cost_usd: Estimated monetary cost
        error_summary: Up to 5 distinct error messages
    """

    stage_type: str
    stage_task_id: Optional[UUID] = None
    duration_ms: int = 0
    provider_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    assets_created: int = 0
    shots_processed: int = 0
    shots_failed: int = 0
    estimated_cost_usd: float = 0.0
    error_summary: List[str] = field(default_factory=list)


@dataclass
class EpisodeMetrics:
    """
    Aggregated metrics across all stages for one Episode.

    Attributes:
        episode_id: UUID of the Episode
        total_duration_ms: Sum of all stage durations
        total_provider_calls: Sum of all Provider calls
        total_assets_created: Sum of all assets created
        total_estimated_cost_usd: Sum of all stage costs
        stages: Per-stage breakdown
    """

    episode_id: UUID
    total_duration_ms: int = 0
    total_provider_calls: int = 0
    total_assets_created: int = 0
    total_estimated_cost_usd: float = 0.0
    stages: List[StageMetrics] = field(default_factory=list)


@dataclass
class ProjectMetrics:
    """
    Aggregated metrics across all episodes for one Project.

    Attributes:
        project_id: UUID of the Project
        total_duration_ms: Sum of all episode durations
        total_provider_calls: Sum of all Provider calls
        total_assets_created: Sum of all assets created
        total_estimated_cost_usd: Sum of all episode costs
        episodes: Per-episode breakdown
    """

    project_id: UUID
    total_duration_ms: int = 0
    total_provider_calls: int = 0
    total_assets_created: int = 0
    total_estimated_cost_usd: float = 0.0
    episodes: List[EpisodeMetrics] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ProviderCallMonitor
# ---------------------------------------------------------------------------


class ProviderCallMonitor:
    """
    Lightweight in-process monitor for Provider API calls.

    Usage (context-manager style)::

        monitor = ProviderCallMonitor()
        with monitor.record_call("stable_diffusion", "generate_image") as ctx:
            result = provider.generate_image(...)
            ctx.request_id = result.request_id
            ctx.success = result.success
            ctx.extra["model"] = "sd_xl_base_1.0"

    After execution, call ``monitor.to_metrics_dict()`` to obtain a
    serialisable summary suitable for storing in ``StageTaskModel.metrics_jsonb``.

    Implements Requirements: 13.1, 13.2, 13.4
    """

    def __init__(self) -> None:
        self._records: List[ProviderCallRecord] = []

    # ------------------------------------------------------------------
    # Context-manager recording
    # ------------------------------------------------------------------

    @contextmanager
    def record_call(
        self,
        provider_name: str,
        operation: str,
    ) -> Generator["_CallContext", None, None]:
        """
        Context manager that records a single Provider call.

        Yields a ``_CallContext`` object whose attributes can be set
        inside the ``with`` block to capture call-specific data.

        Args:
            provider_name: Name of the provider (e.g. 'stable_diffusion')
            operation: Name of the operation (e.g. 'generate_image')

        Yields:
            _CallContext: Mutable context for the call
        """
        ctx = _CallContext(provider_name=provider_name, operation=operation)
        started_at = datetime.utcnow()
        t0 = time.monotonic()

        try:
            yield ctx
        except Exception as exc:
            ctx.success = False
            ctx.error = str(exc)
            raise
        finally:
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._records.append(
                ProviderCallRecord(
                    provider_name=provider_name,
                    operation=operation,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    success=ctx.success,
                    request_id=ctx.request_id,
                    error=ctx.error,
                    extra=ctx.extra,
                )
            )

    # ------------------------------------------------------------------
    # Manual recording (for async / executor-based calls)
    # ------------------------------------------------------------------

    def add_record(
        self,
        provider_name: str,
        operation: str,
        duration_ms: int,
        success: bool,
        request_id: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Manually append a call record.

        Use this when the call is made inside a thread-pool executor and
        the context-manager cannot span the async boundary.

        Implements Requirements: 13.1, 13.4

        Args:
            provider_name: Name of the provider
            operation: Name of the operation
            duration_ms: Duration of the call in milliseconds
            success: Whether the call succeeded
            request_id: Provider-supplied request ID
            error: Error message if failed
            extra: Additional metadata
        """
        self._records.append(
            ProviderCallRecord(
                provider_name=provider_name,
                operation=operation,
                started_at=datetime.utcnow(),
                duration_ms=duration_ms,
                success=success,
                request_id=request_id,
                error=error,
                extra=extra or {},
            )
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def records(self) -> List[ProviderCallRecord]:
        """Return a copy of all recorded calls."""
        return list(self._records)

    def successful_records(self) -> List[ProviderCallRecord]:
        """Return only successful call records."""
        return [r for r in self._records if r.success]

    def failed_records(self) -> List[ProviderCallRecord]:
        """Return only failed call records."""
        return [r for r in self._records if not r.success]

    # ------------------------------------------------------------------
    # Cost estimation (Requirement 13.1, 13.2)
    # ------------------------------------------------------------------

    def estimate_cost(self) -> CostEstimate:
        """
        Estimate the monetary cost of all recorded Provider calls.

        Image cost: IMAGE_COST_PER_CALL × successful image calls
        TTS cost: TTS_COST_PER_1K_CHARS × total characters / 1000

        Implements Requirements: 13.1, 13.2

        Returns:
            CostEstimate with per-provider and total costs
        """
        image_calls = 0
        tts_characters = 0

        for record in self._records:
            if not record.success:
                continue

            if record.operation == "generate_image":
                image_calls += 1
            elif record.operation == "synthesize_speech":
                chars = record.extra.get("character_count", 0) or 0
                tts_characters += int(chars)

        image_cost = image_calls * IMAGE_COST_PER_CALL
        tts_cost = (tts_characters / 1000.0) * TTS_COST_PER_1K_CHARS

        return CostEstimate(
            image_calls=image_calls,
            image_cost_usd=round(image_cost, 6),
            tts_characters=tts_characters,
            tts_cost_usd=round(tts_cost, 6),
            total_cost_usd=round(image_cost + tts_cost, 6),
        )

    # ------------------------------------------------------------------
    # Serialisation for StageTask.metrics_jsonb (Requirement 13.4)
    # ------------------------------------------------------------------

    def to_metrics_dict(self) -> Dict[str, Any]:
        """
        Produce a JSON-serialisable dict suitable for
        ``StageTaskModel.metrics_jsonb``.

        Implements Requirement 13.4

        Returns:
            Dictionary with provider_calls, success_count, failure_count,
            total_duration_ms, estimated_cost, and per-call details.
        """
        cost = self.estimate_cost()
        records = self._records

        total_duration = sum(r.duration_ms for r in records)
        success_count = sum(1 for r in records if r.success)
        failure_count = len(records) - success_count

        # Collect unique errors (up to 10)
        errors = list(
            dict.fromkeys(
                r.error for r in records if not r.success and r.error
            )
        )[:10]

        # Per-call detail list (kept compact)
        call_details = [
            {
                "provider": r.provider_name,
                "operation": r.operation,
                "duration_ms": r.duration_ms,
                "success": r.success,
                "request_id": r.request_id,
                "error": r.error,
            }
            for r in records
        ]

        return {
            "provider_calls": len(records),
            "success_count": success_count,
            "failure_count": failure_count,
            "total_duration_ms": total_duration,
            "estimated_cost_usd": cost.total_cost_usd,
            "image_calls": cost.image_calls,
            "image_cost_usd": cost.image_cost_usd,
            "tts_characters": cost.tts_characters,
            "tts_cost_usd": cost.tts_cost_usd,
            "errors": errors,
            "call_details": call_details,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


class _CallContext:
    """Mutable context object yielded by ``ProviderCallMonitor.record_call``."""

    __slots__ = ("provider_name", "operation", "success", "request_id", "error", "extra")

    def __init__(self, provider_name: str, operation: str) -> None:
        self.provider_name = provider_name
        self.operation = operation
        self.success: bool = True
        self.request_id: Optional[str] = None
        self.error: Optional[str] = None
        self.extra: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# MetricsAggregator — Stage / Episode / Project rollups (Requirement 13.3, 13.5)
# ---------------------------------------------------------------------------


class MetricsAggregator:
    """
    Reads ``StageTaskModel.metrics_jsonb`` records from the database and
    aggregates them at Stage, Episode, and Project granularity.

    Implements Requirements: 13.3, 13.5
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Stage-level (single StageTask)
    # ------------------------------------------------------------------

    def get_stage_metrics(self, stage_task_id: UUID) -> Optional[StageMetrics]:
        """
        Return metrics for a single StageTask.

        Implements Requirement 13.4

        Args:
            stage_task_id: UUID of the StageTask

        Returns:
            StageMetrics or None if not found
        """
        task: Optional[StageTaskModel] = self.db.get(StageTaskModel, stage_task_id)
        if task is None:
            return None

        return self._task_to_stage_metrics(task)

    # ------------------------------------------------------------------
    # Episode-level (all StageTasks for one Episode)
    # ------------------------------------------------------------------

    def get_episode_metrics(self, episode_id: UUID) -> EpisodeMetrics:
        """
        Aggregate metrics across all StageTasks for an Episode.

        Implements Requirement 13.3, 13.5

        Args:
            episode_id: UUID of the Episode

        Returns:
            EpisodeMetrics with per-stage breakdown
        """
        stmt = (
            select(StageTaskModel)
            .where(StageTaskModel.episode_id == episode_id)
            .order_by(StageTaskModel.created_at.asc())
        )
        tasks: List[StageTaskModel] = list(self.db.scalars(stmt).all())

        episode_metrics = EpisodeMetrics(episode_id=episode_id)

        for task in tasks:
            sm = self._task_to_stage_metrics(task)
            episode_metrics.stages.append(sm)
            episode_metrics.total_duration_ms += sm.duration_ms
            episode_metrics.total_provider_calls += sm.provider_calls
            episode_metrics.total_assets_created += sm.assets_created
            episode_metrics.total_estimated_cost_usd += sm.estimated_cost_usd

        episode_metrics.total_estimated_cost_usd = round(
            episode_metrics.total_estimated_cost_usd, 6
        )
        return episode_metrics

    # ------------------------------------------------------------------
    # Project-level (all Episodes for one Project)
    # ------------------------------------------------------------------

    def get_project_metrics(self, project_id: UUID) -> ProjectMetrics:
        """
        Aggregate metrics across all Episodes for a Project.

        Implements Requirement 13.5

        Args:
            project_id: UUID of the Project

        Returns:
            ProjectMetrics with per-episode breakdown
        """
        # Fetch all distinct episode_ids for this project
        stmt = (
            select(EpisodeModel.id)
            .where(EpisodeModel.project_id == project_id)
        )
        episode_ids: List[UUID] = list(self.db.scalars(stmt).all())

        project_metrics = ProjectMetrics(project_id=project_id)

        for ep_id in episode_ids:
            em = self.get_episode_metrics(ep_id)
            project_metrics.episodes.append(em)
            project_metrics.total_duration_ms += em.total_duration_ms
            project_metrics.total_provider_calls += em.total_provider_calls
            project_metrics.total_assets_created += em.total_assets_created
            project_metrics.total_estimated_cost_usd += em.total_estimated_cost_usd

        project_metrics.total_estimated_cost_usd = round(
            project_metrics.total_estimated_cost_usd, 6
        )
        return project_metrics

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _task_to_stage_metrics(task: StageTaskModel) -> StageMetrics:
        """
        Convert a StageTaskModel to a StageMetrics dataclass.

        Reads the ``metrics_jsonb`` field that was written by
        ``ProviderCallMonitor.to_metrics_dict()``.
        """
        m: Dict[str, Any] = task.metrics_jsonb or {}

        # Compute duration from timestamps when not stored in metrics
        duration_ms: int = m.get("duration_ms", 0) or m.get("total_duration_ms", 0)
        if not duration_ms and task.started_at and task.finished_at:
            delta = task.finished_at - task.started_at
            duration_ms = int(delta.total_seconds() * 1000)

        errors: List[str] = m.get("errors", [])
        if isinstance(errors, str):
            errors = [errors]

        return StageMetrics(
            stage_type=task.stage_type,
            stage_task_id=task.id,
            duration_ms=duration_ms,
            provider_calls=m.get("provider_calls", 0),
            success_count=m.get("success_count", 0),
            failure_count=m.get("failure_count", 0),
            retry_count=m.get("retry_count", 0),
            assets_created=m.get("assets_created", 0),
            shots_processed=m.get("shots_processed", 0),
            shots_failed=m.get("shots_failed", 0),
            estimated_cost_usd=m.get("estimated_cost_usd", 0.0),
            error_summary=errors[:5],
        )
