"""
TTS Stage Service

Responsible for synthesizing speech audio for all shots with dialogue
in an episode. Implements parallel processing, retry logic, and asset management.

Implements Requirements: 5.1, 5.2, 5.3, 5.4, 9.1, 9.3, 11.2, 11.3
"""

import asyncio
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import DocumentModel, ShotModel
from app.providers.tts_provider import TTSProviderAdapter, TTSResult, TTSProviderError
from app.repositories.asset_repository import AssetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.services.object_storage_service import ObjectStorageService
from app.services.provider_monitor import ProviderCallMonitor


@dataclass
class DialogueItem:
    """A single dialogue item extracted from a shot."""
    shot_id: UUID
    shot_code: str
    text: str
    character_name: Optional[str] = None
    voice: Optional[str] = None
    language: str = "zh-CN"


@dataclass
class TTSStageResult:
    """Result of the TTS stage execution."""
    status: str  # succeeded, partial_success, failed
    assets_created: int
    shots_processed: int
    shots_failed: int
    errors: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class TTSStage:
    """
    TTS Stage - synthesizes speech audio for all shots with dialogue.

    Responsibilities:
    1. Extract dialogue text from shots and script_draft
    2. Synthesize audio in parallel using TTS Provider
    3. Upload audio to Object Storage
    4. Create Asset records with duration_ms
    5. Handle failures and retries

    Implements Requirements: 5.1, 5.2, 5.3, 5.4, 9.1, 9.3, 11.2, 11.3
    """

    # Default voice used when no character-specific voice is configured
    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
    DEFAULT_LANGUAGE = "zh-CN"
    MAX_RETRIES = 3

    def __init__(
        self,
        db: Session,
        tts_provider: TTSProviderAdapter,
        storage_service: ObjectStorageService,
    ):
        """
        Initialize the TTS Stage.

        Args:
            db: Database session
            tts_provider: TTS provider adapter
            storage_service: Object storage service
        """
        self.db = db
        self.tts_provider = tts_provider
        self.storage_service = storage_service
        self.asset_repo = AssetRepository(db)
        self.document_repo = DocumentRepository(db)
        self.shot_repo = ShotRepository(db)
        self.stage_task_repo = StageTaskRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        episode_id: UUID,
        project_id: UUID,
        stage_task_id: UUID,
        max_concurrent: int = 5,
        monitor: Optional["ProviderCallMonitor"] = None,
    ) -> TTSStageResult:
        """
        Execute the TTS Stage for an episode.

        Implements Requirements: 5.1, 5.2, 5.3, 5.4

        Args:
            episode_id: Episode UUID
            project_id: Project UUID
            stage_task_id: StageTask UUID for tracking
            max_concurrent: Maximum concurrent TTS synthesis calls

        Returns:
            TTSStageResult with execution details
        """
        start_time = time.time()

        # Create a monitor for this execution if not provided
        if monitor is None:
            monitor = ProviderCallMonitor()

        self.stage_task_repo.update_status(
            stage_task_id,
            "running",
            started_at=datetime.utcnow(),
        )

        dialogues: List[DialogueItem] = []

        try:
            # 1. Load shots (Requirement 5.1)
            shots = self.shot_repo.list_current_for_episode(episode_id)

            if not shots:
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.stage_task_repo.update_status(
                    stage_task_id,
                    "succeeded",
                    finished_at=datetime.utcnow(),
                )
                return TTSStageResult(
                    status="succeeded",
                    assets_created=0,
                    shots_processed=0,
                    shots_failed=0,
                    execution_time_ms=execution_time_ms,
                )

            # 2. Load latest script_draft for supplemental dialogue lookup
            script_doc = self._get_latest_script_draft(episode_id)

            # 3. Extract dialogue items (Requirement 5.1)
            dialogues = self._extract_dialogues(shots, script_doc)

            if not dialogues:
                # No dialogue found — succeed with zero assets
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.stage_task_repo.update_status(
                    stage_task_id,
                    "succeeded",
                    finished_at=datetime.utcnow(),
                )
                return TTSStageResult(
                    status="succeeded",
                    assets_created=0,
                    shots_processed=len(shots),
                    shots_failed=0,
                    execution_time_ms=execution_time_ms,
                )

            # 4. Synthesize audio in parallel (Requirements 11.2, 11.3)
            results = await self._synthesize_audio_parallel(dialogues, max_concurrent, monitor)

            # 5. Upload audio and create Asset records (Requirements 5.3, 5.4, 9.1, 9.3)
            assets_created = await self._upload_and_create_assets(
                results=results,
                project_id=project_id,
                episode_id=episode_id,
                stage_task_id=stage_task_id,
            )

            # 6. Compute metrics
            execution_time_ms = int((time.time() - start_time) * 1000)
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            total_chars = sum(r.character_count or 0 for r in successful)
            monitor_metrics = monitor.to_metrics_dict()
            metrics = {
                "duration_ms": execution_time_ms,
                "provider_calls": monitor_metrics.get("provider_calls", len(results)),
                "success_count": monitor_metrics.get("success_count", len(successful)),
                "failure_count": monitor_metrics.get("failure_count", len(failed)),
                "total_characters": total_chars,
                "estimated_cost_usd": monitor_metrics.get("estimated_cost_usd", (total_chars / 1000.0) * 0.016),
                "tts_characters": monitor_metrics.get("tts_characters", total_chars),
                "tts_cost_usd": monitor_metrics.get("tts_cost_usd", 0.0),
                "call_details": monitor_metrics.get("call_details", []),
                "errors": monitor_metrics.get("errors", []),
            }

            # 7. Determine final status
            if not failed:
                final_status = "succeeded"
                task_status = "succeeded"
            elif successful:
                final_status = "partial_success"
                task_status = "succeeded"
            else:
                final_status = "failed"
                task_status = "failed"

            # Persist metrics to StageTask (Requirement 13.2)
            self.stage_task_repo.update_metrics(
                stage_task_id,
                metrics=metrics,
                commit=False,
            )
            self.stage_task_repo.update_status(
                stage_task_id,
                task_status,
                finished_at=datetime.utcnow(),
            )

            return TTSStageResult(
                status=final_status,
                assets_created=assets_created,
                shots_processed=len(successful),
                shots_failed=len(failed),
                errors=[r.error for r in failed if r.error],
                execution_time_ms=execution_time_ms,
                metrics=metrics,
            )

        except Exception as exc:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.stage_task_repo.update_status(
                stage_task_id,
                "failed",
                finished_at=datetime.utcnow(),
                error_message=str(exc),
            )
            return TTSStageResult(
                status="failed",
                assets_created=0,
                shots_processed=0,
                shots_failed=len(dialogues),
                errors=[str(exc)],
                execution_time_ms=execution_time_ms,
            )

    # ------------------------------------------------------------------
    # Dialogue extraction (Requirement 5.1)
    # ------------------------------------------------------------------

    def _get_latest_script_draft(self, episode_id: UUID) -> Optional[DocumentModel]:
        """Return the latest script_draft document for the episode, or None."""
        docs = self.document_repo.list_for_episode(episode_id)
        script_docs = [d for d in docs if d.document_type == "script_draft"]
        return script_docs[0] if script_docs else None

    def _extract_dialogues(
        self,
        shots: List[ShotModel],
        script_doc: Optional[DocumentModel],
    ) -> List[DialogueItem]:
        """
        Extract dialogue items from shots and optional script document.

        Priority: shot.dialogue_text > script_draft lookup.
        Only shots with non-empty dialogue produce a DialogueItem.

        Implements Requirement 5.1
        """
        # Build supplemental lookup from script document
        script_lookup: Dict[str, Dict[str, str]] = {}
        if script_doc and script_doc.content_jsonb:
            script_lookup = self._extract_script_dialogue_lookup(script_doc.content_jsonb)

        items: List[DialogueItem] = []
        for shot in shots:
            text = shot.dialogue_text or ""
            character_name: Optional[str] = None
            voice: Optional[str] = None

            # Fall back to script lookup if shot has no direct dialogue
            if not text.strip() and shot.shot_code in script_lookup:
                entry = script_lookup[shot.shot_code]
                text = entry.get("dialogue", "")
                character_name = entry.get("character")
                voice = entry.get("voice")

            # Extract character from shot's characters_jsonb if not already set
            if not character_name and shot.characters_jsonb:
                character_name = self._extract_primary_character(shot.characters_jsonb)

            text = text.strip()
            if not text:
                continue  # Skip shots with no dialogue

            items.append(
                DialogueItem(
                    shot_id=shot.id,
                    shot_code=shot.shot_code,
                    text=text,
                    character_name=character_name,
                    voice=voice or self.DEFAULT_VOICE,
                    language=self.DEFAULT_LANGUAGE,
                )
            )

        return items

    def _extract_script_dialogue_lookup(
        self, content_jsonb: dict
    ) -> Dict[str, Dict[str, str]]:
        """
        Build a shot_code -> {dialogue, character, voice} mapping from script content.

        Handles the common structure: {"shots": [{"shot_code": ..., "dialogue": ..., ...}]}
        """
        lookup: Dict[str, Dict[str, str]] = {}
        shots_list = content_jsonb.get("shots", [])
        for item in shots_list:
            if not isinstance(item, dict):
                continue
            code = item.get("shot_code") or item.get("code")
            if not code:
                continue
            lookup[code] = {
                "dialogue": item.get("dialogue") or item.get("dialogue_text") or "",
                "character": item.get("character") or item.get("character_name") or "",
                "voice": item.get("voice") or "",
            }
        return lookup

    def _extract_primary_character(self, characters_jsonb: list) -> Optional[str]:
        """
        Extract the primary (first) character name from a shot's characters list.

        The characters_jsonb field may contain strings or dicts with a 'name' key.
        """
        if not characters_jsonb:
            return None
        first = characters_jsonb[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("name") or first.get("character_name")
        return None

    # ------------------------------------------------------------------
    # Parallel synthesis (Requirements 11.2, 11.3)
    # ------------------------------------------------------------------

    async def _synthesize_audio_parallel(
        self,
        dialogues: List[DialogueItem],
        max_concurrent: int,
        monitor: "ProviderCallMonitor",
    ) -> List[TTSResult]:
        """
        Synthesize audio for all dialogue items in parallel.

        Uses asyncio.Semaphore to cap concurrent Provider calls.

        Implements Requirements 11.2, 11.3
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def synthesize_with_semaphore(item: DialogueItem) -> TTSResult:
            async with semaphore:
                return await self._synthesize_single_with_retry(item, monitor)

        tasks = [synthesize_with_semaphore(d) for d in dialogues]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert any unexpected exceptions into failed TTSResult objects
        results: List[TTSResult] = []
        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                results.append(
                    TTSResult(
                        success=False,
                        error=str(res),
                        shot_id=dialogues[i].shot_id,
                    )
                )
            else:
                results.append(res)

        return results

    async def _synthesize_single_with_retry(
        self,
        item: DialogueItem,
        monitor: "ProviderCallMonitor",
    ) -> TTSResult:
        """
        Synthesize a single dialogue item with exponential-backoff retry,
        recording each attempt via the monitor.

        Implements Requirements 12.1, 12.2, 12.3, 13.1
        """
        last_error: Optional[str] = None

        for attempt in range(self.MAX_RETRIES):
            t0 = time.time()
            try:
                loop = asyncio.get_event_loop()
                result: TTSResult = await loop.run_in_executor(
                    None,
                    lambda: self.tts_provider.synthesize_speech(
                        text=item.text,
                        voice=item.voice or self.DEFAULT_VOICE,
                        language=item.language,
                        shot_id=item.shot_id,
                    ),
                )

                duration_ms = int((time.time() - t0) * 1000)
                # Record the call (Requirement 13.1)
                monitor.add_record(
                    provider_name=self.tts_provider.provider_name,
                    operation="synthesize_speech",
                    duration_ms=duration_ms,
                    success=result.success,
                    request_id=result.request_id,
                    error=result.error if not result.success else None,
                    extra={
                        "shot_id": str(item.shot_id),
                        "character_count": result.character_count or len(item.text),
                    },
                )

                if result.success:
                    return result

                last_error = result.error
                break

            except TTSProviderError as exc:
                duration_ms = int((time.time() - t0) * 1000)
                last_error = str(exc)

                monitor.add_record(
                    provider_name=self.tts_provider.provider_name,
                    operation="synthesize_speech",
                    duration_ms=duration_ms,
                    success=False,
                    request_id=exc.request_id,
                    error=str(exc),
                    extra={"shot_id": str(item.shot_id), "attempt": attempt},
                )

                if not exc.is_retryable or attempt == self.MAX_RETRIES - 1:
                    break
                wait_secs = 2 ** attempt
                await asyncio.sleep(wait_secs)

            except Exception as exc:
                duration_ms = int((time.time() - t0) * 1000)
                last_error = f"Unexpected error: {exc}"
                monitor.add_record(
                    provider_name=self.tts_provider.provider_name,
                    operation="synthesize_speech",
                    duration_ms=duration_ms,
                    success=False,
                    error=last_error,
                    extra={"shot_id": str(item.shot_id)},
                )
                break

        return TTSResult(
            success=False,
            error=last_error or "Unknown error",
            shot_id=item.shot_id,
        )

    # ------------------------------------------------------------------
    # Upload and asset creation (Requirements 5.3, 5.4, 9.1, 9.3)
    # ------------------------------------------------------------------

    async def _upload_and_create_assets(
        self,
        results: List[TTSResult],
        project_id: UUID,
        episode_id: UUID,
        stage_task_id: UUID,
    ) -> int:
        """
        Save audio data to temp files, upload to Object Storage, and create Asset records.

        Implements Requirements 5.3, 5.4, 9.1, 9.3
        """
        assets_created = 0

        for result in results:
            if not result.success or not result.audio_data:
                continue

            tmp_path: Optional[str] = None
            try:
                audio_format = result.audio_format or "wav"
                mime_type = f"audio/{audio_format}"

                # 1. Write audio to a temporary file
                fd, tmp_path = tempfile.mkstemp(suffix=f".{audio_format}")
                try:
                    os.write(fd, result.audio_data)
                finally:
                    os.close(fd)

                # 2. Generate storage key
                storage_key = self.storage_service.generate_storage_key(
                    project_id=str(project_id),
                    episode_id=str(episode_id),
                    asset_type="audio",
                    file_extension=audio_format,
                )

                # 3. Upload to Object Storage
                loop = asyncio.get_event_loop()
                upload_result = await loop.run_in_executor(
                    None,
                    lambda: self.storage_service.upload_file(
                        file_path=tmp_path,
                        storage_key=storage_key,
                        content_type=mime_type,
                        metadata={
                            "shot_id": str(result.shot_id) if result.shot_id else "",
                            "stage_task_id": str(stage_task_id),
                        },
                    ),
                )

                # 4. Create Asset record (including duration_ms per Requirement 9.3)
                self.asset_repo.create_asset(
                    project_id=project_id,
                    episode_id=episode_id,
                    shot_id=result.shot_id,
                    stage_task_id=stage_task_id,
                    asset_type="audio",
                    storage_key=upload_result.storage_key,
                    mime_type=mime_type,
                    size_bytes=upload_result.size_bytes,
                    duration_ms=result.duration_ms,
                    is_selected=True,
                    metadata_jsonb=result.provider_metadata or {},
                )

                assets_created += 1

            except Exception as exc:
                # Log and continue — single failure must not block others (Req 5.5)
                print(f"Error uploading audio asset for shot {result.shot_id}: {exc}")

            finally:
                # 5. Clean up temporary file
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        return assets_created
