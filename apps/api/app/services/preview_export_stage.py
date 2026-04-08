"""
Preview Export Stage Service

Responsible for compositing a preview video for an episode by:
1. Collecting primary keyframe, audio, and subtitle assets for each shot
2. Downloading those assets to a temporary working directory
3. Using FFmpeg to stitch them into a 720p H.264 preview video
4. Uploading the result to Object Storage and creating an Asset record

Implements Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AssetModel, ShotModel
from app.repositories.asset_repository import AssetRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository
from app.services.object_storage_service import ObjectStorageService


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ShotAssets:
    """Primary assets collected for a single shot."""
    shot: ShotModel
    keyframe: Optional[AssetModel] = None
    audio: Optional[AssetModel] = None


@dataclass
class PreviewExportResult:
    """Result of the Preview Export Stage execution."""
    status: str  # succeeded, failed
    assets_created: int
    shots_collected: int
    errors: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    metrics: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage implementation
# ---------------------------------------------------------------------------

class PreviewExportStage:
    """
    Preview Export Stage – composites a preview video for an episode.

    Responsibilities:
    1. Collect primary keyframe / audio assets per shot  (Req 7.1)
    2. Download assets to a temp directory               (Req 7.1)
    3. Compose video with FFmpeg                         (Req 7.2, 7.3)
    4. Upload preview video and create Asset record      (Req 7.4)
    5. Clean up temporary files                          (Req 7.4)

    Implements Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """

    # Output video parameters (Requirement 7.3 – 720p H.264)
    OUTPUT_WIDTH = 1280
    OUTPUT_HEIGHT = 720
    VIDEO_CODEC = "libx264"
    AUDIO_CODEC = "aac"
    PIX_FMT = "yuv420p"
    CRF = 23  # quality factor for H.264

    def __init__(
        self,
        db: Session,
        storage_service: ObjectStorageService,
    ) -> None:
        """
        Initialize the Preview Export Stage.

        Args:
            db: Database session
            storage_service: Object storage service
        """
        self.db = db
        self.storage_service = storage_service
        self.asset_repo = AssetRepository(db)
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
    ) -> PreviewExportResult:
        """
        Execute the Preview Export Stage for an episode.

        Implements Requirements: 7.1, 7.2, 7.3, 7.4

        Args:
            episode_id: Episode UUID
            project_id: Project UUID
            stage_task_id: StageTask UUID for tracking

        Returns:
            PreviewExportResult with execution details
        """
        start_time = time.time()

        self.stage_task_repo.update_status(
            stage_task_id,
            "running",
            started_at=datetime.utcnow(),
        )

        temp_dir: Optional[str] = None

        try:
            # 1. Collect primary assets per shot (Requirement 7.1)
            shots = self.shot_repo.list_current_for_episode(episode_id)
            if not shots:
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.stage_task_repo.update_status(
                    stage_task_id,
                    "failed",
                    finished_at=datetime.utcnow(),
                    error_message="No shots found for episode",
                )
                return PreviewExportResult(
                    status="failed",
                    assets_created=0,
                    shots_collected=0,
                    errors=["No shots found for episode"],
                    execution_time_ms=execution_time_ms,
                )

            shot_assets_list = self._collect_primary_assets(shots)

            # Require at least one keyframe to proceed
            shots_with_keyframe = [sa for sa in shot_assets_list if sa.keyframe is not None]
            if not shots_with_keyframe:
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.stage_task_repo.update_status(
                    stage_task_id,
                    "failed",
                    finished_at=datetime.utcnow(),
                    error_message="No keyframe assets found for episode",
                )
                return PreviewExportResult(
                    status="failed",
                    assets_created=0,
                    shots_collected=0,
                    errors=["No keyframe assets found for episode"],
                    execution_time_ms=execution_time_ms,
                )

            # 2. Get subtitle asset for the episode (Requirement 7.1)
            subtitle_asset = self._get_subtitle_asset(episode_id)

            # 3. Create temp working directory and download assets (Requirement 7.1)
            temp_dir = tempfile.mkdtemp(prefix="preview_export_")
            self._download_assets(shot_assets_list, subtitle_asset, temp_dir)

            # 4. Compose video with FFmpeg (Requirements 7.2, 7.3)
            output_path = os.path.join(temp_dir, "preview.mp4")
            duration_ms = self._compose_video(
                shot_assets_list=shot_assets_list,
                subtitle_asset=subtitle_asset,
                temp_dir=temp_dir,
                output_path=output_path,
            )

            # 5. Upload preview video and create Asset record (Requirement 7.4)
            assets_created = self._upload_preview(
                video_path=output_path,
                project_id=project_id,
                episode_id=episode_id,
                stage_task_id=stage_task_id,
                duration_ms=duration_ms,
            )

            execution_time_ms = int((time.time() - start_time) * 1000)
            self.stage_task_repo.update_status(
                stage_task_id,
                "succeeded",
                finished_at=datetime.utcnow(),
            )

            return PreviewExportResult(
                status="succeeded",
                assets_created=assets_created,
                shots_collected=len(shots_with_keyframe),
                execution_time_ms=execution_time_ms,
                metrics={
                    "duration_ms": execution_time_ms,
                    "shots_with_keyframe": len(shots_with_keyframe),
                    "shots_with_audio": sum(1 for sa in shot_assets_list if sa.audio),
                    "has_subtitle": subtitle_asset is not None,
                    "preview_duration_ms": duration_ms,
                },
            )

        except Exception as exc:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.stage_task_repo.update_status(
                stage_task_id,
                "failed",
                finished_at=datetime.utcnow(),
                error_message=str(exc),
            )
            return PreviewExportResult(
                status="failed",
                assets_created=0,
                shots_collected=0,
                errors=[str(exc)],
                execution_time_ms=execution_time_ms,
            )

        finally:
            # Always clean up temp directory (Requirement 7.4)
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except OSError as exc:
                    print(f"Warning: failed to remove temp dir {temp_dir}: {exc}")

    # ------------------------------------------------------------------
    # 7.2 Primary asset collection (Requirement 7.1)
    # ------------------------------------------------------------------

    def _collect_primary_assets(self, shots: List[ShotModel]) -> List[ShotAssets]:
        """
        For each shot, retrieve the primary (is_selected=True) keyframe and audio assets.

        Implements Requirement 7.1
        """
        result: List[ShotAssets] = []
        for shot in shots:
            keyframe = self.asset_repo.get_selected_asset_by_shot(
                shot_id=shot.id,
                asset_type="keyframe",
            )
            audio = self.asset_repo.get_selected_asset_by_shot(
                shot_id=shot.id,
                asset_type="audio",
            )
            result.append(ShotAssets(shot=shot, keyframe=keyframe, audio=audio))
        return result

    def _get_subtitle_asset(self, episode_id: UUID) -> Optional[AssetModel]:
        """
        Retrieve the most recent selected subtitle asset for the episode.

        Implements Requirement 7.1
        """
        assets = self.asset_repo.list_selected_for_episode(episode_id)
        subtitle_assets = [a for a in assets if a.asset_type == "subtitle"]
        return subtitle_assets[0] if subtitle_assets else None

    # ------------------------------------------------------------------
    # 7.3 Asset download (Requirement 7.1)
    # ------------------------------------------------------------------

    def _download_assets(
        self,
        shot_assets_list: List[ShotAssets],
        subtitle_asset: Optional[AssetModel],
        temp_dir: str,
    ) -> None:
        """
        Download all required assets into temp_dir.

        Files are named deterministically so FFmpeg can reference them:
          keyframes/  shot_{idx:04d}.{ext}
          audio/      shot_{idx:04d}.{ext}
          subtitle.vtt

        Implements Requirement 7.1
        """
        keyframe_dir = os.path.join(temp_dir, "keyframes")
        audio_dir = os.path.join(temp_dir, "audio")
        os.makedirs(keyframe_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)

        for idx, sa in enumerate(shot_assets_list):
            if sa.keyframe:
                ext = self._ext_from_mime(sa.keyframe.mime_type, default="png")
                local_path = os.path.join(keyframe_dir, f"shot_{idx:04d}.{ext}")
                self.storage_service.download_file(sa.keyframe.storage_key, local_path)
                # Verify file was downloaded
                if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
                    raise RuntimeError(
                        f"Failed to download keyframe for shot {sa.shot.shot_code}"
                    )

            if sa.audio:
                ext = self._ext_from_mime(sa.audio.mime_type, default="mp3")
                local_path = os.path.join(audio_dir, f"shot_{idx:04d}.{ext}")
                self.storage_service.download_file(sa.audio.storage_key, local_path)

        if subtitle_asset:
            subtitle_path = os.path.join(temp_dir, "subtitle.vtt")
            self.storage_service.download_file(subtitle_asset.storage_key, subtitle_path)

    # ------------------------------------------------------------------
    # 7.4 FFmpeg video composition (Requirements 7.2, 7.3)
    # ------------------------------------------------------------------

    def _compose_video(
        self,
        shot_assets_list: List[ShotAssets],
        subtitle_asset: Optional[AssetModel],
        temp_dir: str,
        output_path: str,
    ) -> int:
        """
        Compose the preview video using FFmpeg.

        Strategy:
        - Each shot with a keyframe becomes a video segment (still image held for
          shot.duration_ms milliseconds).
        - If the shot has a corresponding audio file it is mixed in for that segment.
        - Segments are concatenated via the FFmpeg concat demuxer.
        - Subtitles are burned in if a subtitle file is present.
        - Output: 720p H.264 / AAC, yuv420p.

        Returns the total duration of the composed video in milliseconds.

        Implements Requirements 7.2, 7.3
        """
        keyframe_dir = os.path.join(temp_dir, "keyframes")
        audio_dir = os.path.join(temp_dir, "audio")

        # Build per-shot segment videos, then concatenate
        segment_paths: List[str] = []
        total_duration_ms = 0

        for idx, sa in enumerate(shot_assets_list):
            if sa.keyframe is None:
                continue  # skip shots without a keyframe

            duration_ms = sa.shot.duration_ms or 3000  # default 3 s
            duration_sec = duration_ms / 1000.0
            total_duration_ms += duration_ms

            kf_ext = self._ext_from_mime(sa.keyframe.mime_type, default="png")
            kf_path = os.path.join(keyframe_dir, f"shot_{idx:04d}.{kf_ext}")

            segment_path = os.path.join(temp_dir, f"segment_{idx:04d}.mp4")

            # Check for audio
            audio_path: Optional[str] = None
            if sa.audio:
                a_ext = self._ext_from_mime(sa.audio.mime_type, default="mp3")
                candidate = os.path.join(audio_dir, f"shot_{idx:04d}.{a_ext}")
                if os.path.exists(candidate):
                    audio_path = candidate

            self._build_segment(
                keyframe_path=kf_path,
                audio_path=audio_path,
                duration_sec=duration_sec,
                output_path=segment_path,
            )
            segment_paths.append(segment_path)

        if not segment_paths:
            raise RuntimeError("No video segments could be created (no keyframes downloaded)")

        # Write concat list file
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for seg in segment_paths:
                # FFmpeg concat demuxer requires forward slashes on all platforms
                f.write(f"file '{seg.replace(os.sep, '/')}'\n")

        # Concatenate segments
        concat_output = os.path.join(temp_dir, "concat.mp4")
        self._run_ffmpeg_concat(concat_list_path, concat_output)

        # Burn in subtitles if available
        subtitle_path = os.path.join(temp_dir, "subtitle.vtt")
        if subtitle_asset and os.path.exists(subtitle_path):
            self._burn_subtitles(concat_output, subtitle_path, output_path)
        else:
            # Just copy/re-encode to final output path
            os.rename(concat_output, output_path)

        return total_duration_ms

    def _build_segment(
        self,
        keyframe_path: str,
        audio_path: Optional[str],
        duration_sec: float,
        output_path: str,
    ) -> None:
        """
        Build a single video segment from a still image (+ optional audio).

        Implements Requirement 7.2
        """
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", str(duration_sec),
            "-i", keyframe_path,
        ]

        if audio_path:
            cmd += ["-i", audio_path]

        cmd += [
            "-c:v", self.VIDEO_CODEC,
            "-pix_fmt", self.PIX_FMT,
            "-crf", str(self.CRF),
            "-vf", f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
                   f"pad={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-r", "24",
            "-t", str(duration_sec),
        ]

        if audio_path:
            cmd += ["-c:a", self.AUDIO_CODEC, "-shortest"]
        else:
            cmd += ["-an"]  # no audio stream

        cmd.append(output_path)

        self._run_ffmpeg(cmd, context=f"building segment {output_path}")

    def _run_ffmpeg_concat(self, concat_list_path: str, output_path: str) -> None:
        """
        Concatenate segment files using the FFmpeg concat demuxer.

        Implements Requirement 7.2
        """
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c:v", self.VIDEO_CODEC,
            "-pix_fmt", self.PIX_FMT,
            "-crf", str(self.CRF),
            "-c:a", self.AUDIO_CODEC,
            output_path,
        ]
        self._run_ffmpeg(cmd, context="concatenating segments")

    def _burn_subtitles(
        self, input_path: str, subtitle_path: str, output_path: str
    ) -> None:
        """
        Burn VTT subtitles into the video.

        Implements Requirement 7.2
        """
        # FFmpeg subtitles filter requires the path to use forward slashes and
        # special characters to be escaped on Windows.
        safe_sub = subtitle_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"subtitles='{safe_sub}'",
            "-c:v", self.VIDEO_CODEC,
            "-pix_fmt", self.PIX_FMT,
            "-crf", str(self.CRF),
            "-c:a", self.AUDIO_CODEC,
            output_path,
        ]
        self._run_ffmpeg(cmd, context="burning subtitles")

    @staticmethod
    def _run_ffmpeg(cmd: List[str], context: str = "") -> None:
        """
        Run an FFmpeg command, raising RuntimeError on failure.

        Implements Requirement 7.2
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5-minute timeout per operation
            )
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg executable not found. Please install FFmpeg and ensure it is on PATH."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FFmpeg timed out while {context}")

        if result.returncode != 0:
            stderr_text = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"FFmpeg failed while {context} (exit {result.returncode}):\n{stderr_text}"
            )

    # ------------------------------------------------------------------
    # 7.5 Upload and asset record creation (Requirement 7.4)
    # ------------------------------------------------------------------

    def _upload_preview(
        self,
        video_path: str,
        project_id: UUID,
        episode_id: UUID,
        stage_task_id: UUID,
        duration_ms: int,
    ) -> int:
        """
        Upload the composed preview video to Object Storage and create an Asset record.

        Implements Requirement 7.4

        Returns:
            Number of assets created (0 or 1)
        """
        if not os.path.exists(video_path):
            raise RuntimeError(f"Preview video not found at {video_path}")

        storage_key = self.storage_service.generate_storage_key(
            project_id=str(project_id),
            episode_id=str(episode_id),
            asset_type="preview",
            file_extension="mp4",
        )

        upload_result = self.storage_service.upload_file(
            file_path=video_path,
            storage_key=storage_key,
            content_type="video/mp4",
            metadata={
                "episode_id": str(episode_id),
                "stage_task_id": str(stage_task_id),
            },
        )

        self.asset_repo.create_asset(
            project_id=project_id,
            episode_id=episode_id,
            stage_task_id=stage_task_id,
            asset_type="preview",
            storage_key=upload_result.storage_key,
            mime_type="video/mp4",
            size_bytes=upload_result.size_bytes,
            duration_ms=duration_ms,
            width=self.OUTPUT_WIDTH,
            height=self.OUTPUT_HEIGHT,
            is_selected=True,
            metadata_jsonb={
                "codec": self.VIDEO_CODEC,
                "resolution": f"{self.OUTPUT_WIDTH}x{self.OUTPUT_HEIGHT}",
            },
        )

        return 1

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _ext_from_mime(mime_type: str, default: str = "bin") -> str:
        """
        Derive a file extension from a MIME type string.

        Examples:
            "image/png"  -> "png"
            "audio/mpeg" -> "mp3"
            "video/mp4"  -> "mp4"
            "text/vtt"   -> "vtt"
        """
        _MIME_TO_EXT: Dict[str, str] = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/webp": "webp",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg",
            "audio/aac": "aac",
            "video/mp4": "mp4",
            "text/vtt": "vtt",
        }
        if mime_type in _MIME_TO_EXT:
            return _MIME_TO_EXT[mime_type]
        # Fallback: take the part after '/'
        parts = mime_type.split("/")
        if len(parts) == 2 and parts[1]:
            return parts[1].split(";")[0].strip()
        return default
