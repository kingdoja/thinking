"""
Subtitle Generation Stage Service

Responsible for generating subtitle files (VTT format) for an episode
by extracting dialogue from script_draft and computing timelines from shot durations.

Implements Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import DocumentModel, ShotModel
from app.repositories.asset_repository import AssetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.services.object_storage_service import ObjectStorageService


@dataclass
class SubtitleEntry:
    """A single subtitle cue with timing and text."""
    start_ms: int
    end_ms: int
    text: str
    shot_id: Optional[UUID] = None


@dataclass
class SubtitleGenerationResult:
    """Result of the subtitle generation stage."""
    status: str  # succeeded, failed
    assets_created: int
    shots_processed: int
    errors: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class SubtitleGenerationStage:
    """
    Subtitle Generation Stage - generates VTT subtitle files for an episode.

    Responsibilities:
    1. Load script_draft document and shots for the episode
    2. Extract dialogue/narration text per shot
    3. Compute subtitle timeline from shot duration_ms values
    4. Generate a WebVTT-formatted subtitle file
    5. Upload the file to Object Storage and create an Asset record

    Implements Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """

    def __init__(
        self,
        db: Session,
        storage_service: ObjectStorageService,
    ):
        """
        Initialize the Subtitle Generation Stage.

        Args:
            db: Database session
            storage_service: Object storage service for uploading subtitle files
        """
        self.db = db
        self.storage_service = storage_service
        self.asset_repo = AssetRepository(db)
        self.document_repo = DocumentRepository(db)
        self.shot_repo = ShotRepository(db)
        self.stage_task_repo = StageTaskRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        episode_id: UUID,
        project_id: UUID,
        stage_task_id: UUID,
    ) -> SubtitleGenerationResult:
        """
        Execute the Subtitle Generation Stage for an episode.

        Implements Requirements: 4.1, 4.2, 4.3, 4.4

        Args:
            episode_id: Episode UUID
            project_id: Project UUID
            stage_task_id: StageTask UUID for tracking

        Returns:
            SubtitleGenerationResult with execution details
        """
        start_time = time.time()

        self.stage_task_repo.update_status(
            stage_task_id,
            "running",
            started_at=datetime.utcnow(),
        )

        try:
            # 1. Load shots ordered by scene/shot number (Requirement 4.1)
            shots = self.shot_repo.list_current_for_episode(episode_id)

            if not shots:
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.stage_task_repo.update_status(
                    stage_task_id,
                    "succeeded",
                    finished_at=datetime.utcnow(),
                )
                return SubtitleGenerationResult(
                    status="succeeded",
                    assets_created=0,
                    shots_processed=0,
                    execution_time_ms=execution_time_ms,
                )

            # 2. Load latest script_draft (Requirement 4.1)
            script_doc = self._get_latest_script_draft(episode_id)

            # 3. Build subtitle entries (Requirements 4.1, 4.2)
            entries = self._build_subtitle_entries(shots, script_doc)

            # 4. Generate VTT content (Requirement 4.3)
            vtt_content = self._generate_vtt(entries)

            # 5. Save to temp file, upload, create Asset (Requirement 4.4)
            assets_created = self._upload_subtitle(
                vtt_content=vtt_content,
                project_id=project_id,
                episode_id=episode_id,
                stage_task_id=stage_task_id,
            )

            execution_time_ms = int((time.time() - start_time) * 1000)
            self.stage_task_repo.update_status(
                stage_task_id,
                "succeeded",
                finished_at=datetime.utcnow(),
            )

            return SubtitleGenerationResult(
                status="succeeded",
                assets_created=assets_created,
                shots_processed=len(shots),
                execution_time_ms=execution_time_ms,
                metrics={"subtitle_entries": len(entries)},
            )

        except Exception as exc:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.stage_task_repo.update_status(
                stage_task_id,
                "failed",
                finished_at=datetime.utcnow(),
                error_message=str(exc),
            )
            return SubtitleGenerationResult(
                status="failed",
                assets_created=0,
                shots_processed=0,
                errors=[str(exc)],
                execution_time_ms=execution_time_ms,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_latest_script_draft(self, episode_id: UUID) -> Optional[DocumentModel]:
        """
        Return the latest script_draft document for the episode, or None.

        Implements Requirement 4.1
        """
        docs = self.document_repo.list_for_episode(episode_id)
        script_docs = [d for d in docs if d.document_type == "script_draft"]
        if not script_docs:
            return None
        # list_for_episode already orders by updated_at desc
        return script_docs[0]

    def _build_subtitle_entries(
        self,
        shots: List[ShotModel],
        script_doc: Optional[DocumentModel],
    ) -> List[SubtitleEntry]:
        """
        Build subtitle entries from shots and optional script document.

        Timeline is computed by accumulating shot duration_ms values.
        Text is taken from shot.dialogue_text when available; otherwise
        the script document is consulted for a matching shot entry.

        Implements Requirements 4.1, 4.2
        """
        # Build a lookup from shot_code -> dialogue text from the script doc
        script_lookup: Dict[str, str] = {}
        if script_doc and script_doc.content_jsonb:
            script_lookup = self._extract_script_lookup(script_doc.content_jsonb)

        entries: List[SubtitleEntry] = []
        current_ms = 0

        for shot in shots:
            duration = shot.duration_ms or 0
            start_ms = current_ms
            end_ms = current_ms + duration

            # Prefer shot.dialogue_text; fall back to script lookup
            text = shot.dialogue_text or script_lookup.get(shot.shot_code, "")
            text = self._sanitize_text(text)

            if text:
                entries.append(
                    SubtitleEntry(
                        start_ms=start_ms,
                        end_ms=end_ms,
                        text=text,
                        shot_id=shot.id,
                    )
                )

            current_ms = end_ms

        return entries

    def _extract_script_lookup(self, content_jsonb: dict) -> Dict[str, str]:
        """
        Extract a shot_code -> dialogue mapping from a script document's content.

        The script document may store shots under various keys; we try common
        structures used in this codebase.
        """
        lookup: Dict[str, str] = {}

        # Structure: {"shots": [{"shot_code": "...", "dialogue": "..."}]}
        shots_list = content_jsonb.get("shots", [])
        for item in shots_list:
            if not isinstance(item, dict):
                continue
            code = item.get("shot_code") or item.get("code")
            dialogue = item.get("dialogue") or item.get("dialogue_text") or ""
            if code and dialogue:
                lookup[code] = dialogue

        return lookup

    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize subtitle text: strip leading/trailing whitespace and
        collapse internal runs of whitespace/newlines to a single space.

        Handles special characters that could break VTT parsing.
        """
        if not text:
            return ""
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Escape VTT-reserved sequences (bare '-->' in text)
        text = text.replace("-->", "- ->")
        return text

    def _generate_vtt(self, entries: List[SubtitleEntry]) -> str:
        """
        Generate a WebVTT string from subtitle entries.

        Format:
            WEBVTT

            00:00:00.000 --> 00:00:05.000
            Dialogue text here

        Implements Requirement 4.3
        """
        lines = ["WEBVTT", ""]

        for idx, entry in enumerate(entries, start=1):
            start = self._ms_to_vtt_timestamp(entry.start_ms)
            end = self._ms_to_vtt_timestamp(entry.end_ms)
            lines.append(str(idx))
            lines.append(f"{start} --> {end}")
            lines.append(entry.text)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _ms_to_vtt_timestamp(ms: int) -> str:
        """
        Convert milliseconds to WebVTT timestamp format HH:MM:SS.mmm.

        Args:
            ms: Time in milliseconds (non-negative)

        Returns:
            Formatted timestamp string, e.g. "00:01:23.456"
        """
        ms = max(0, ms)
        hours = ms // 3_600_000
        ms %= 3_600_000
        minutes = ms // 60_000
        ms %= 60_000
        seconds = ms // 1_000
        millis = ms % 1_000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    def _upload_subtitle(
        self,
        vtt_content: str,
        project_id: UUID,
        episode_id: UUID,
        stage_task_id: UUID,
    ) -> int:
        """
        Save VTT content to a temp file, upload to Object Storage, and
        create an Asset record.

        Implements Requirement 4.4

        Returns:
            Number of assets created (0 or 1)
        """
        tmp_path: Optional[str] = None
        try:
            # Write to temp file
            fd, tmp_path = tempfile.mkstemp(suffix=".vtt")
            try:
                os.write(fd, vtt_content.encode("utf-8"))
            finally:
                os.close(fd)

            # Generate storage key
            storage_key = self.storage_service.generate_storage_key(
                project_id=str(project_id),
                episode_id=str(episode_id),
                asset_type="subtitle",
                file_extension="vtt",
            )

            # Upload
            upload_result = self.storage_service.upload_file(
                file_path=tmp_path,
                storage_key=storage_key,
                content_type="text/vtt",
                metadata={
                    "episode_id": str(episode_id),
                    "stage_task_id": str(stage_task_id),
                },
            )

            # Create Asset record
            self.asset_repo.create_asset(
                project_id=project_id,
                episode_id=episode_id,
                stage_task_id=stage_task_id,
                asset_type="subtitle",
                storage_key=upload_result.storage_key,
                mime_type="text/vtt",
                size_bytes=upload_result.size_bytes,
                is_selected=True,
            )

            return 1

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
