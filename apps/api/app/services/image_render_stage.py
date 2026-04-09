"""
Image Render Stage Service

Responsible for generating keyframe images for all shots in an episode.
Implements parallel processing, retry logic, and asset management.

Implements Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 11.1, 11.3, 12.1, 12.2, 12.3
"""

import asyncio
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.providers.image_provider import ImageProviderAdapter, ImageGenerationResult, ProviderError
from app.services.object_storage_service import ObjectStorageService
from app.services.image_render_input_builder import ImageRenderInputBuilder, ImageRenderInput
from app.services.provider_monitor import ProviderCallMonitor
from app.repositories.asset_repository import AssetRepository
from app.repositories.shot_repository import ShotRepository
from app.repositories.stage_task_repository import StageTaskRepository


@dataclass
class StageExecutionResult:
    """Result of a stage execution."""
    status: str  # succeeded, partial_success, failed
    assets_created: int
    shots_processed: int
    shots_failed: int
    errors: List[str]
    execution_time_ms: int
    metrics: Dict[str, Any]


@dataclass
class ImageGenerationTask:
    """Task for generating a single image."""
    input_data: ImageRenderInput
    attempt: int = 0
    last_error: Optional[str] = None


class ImageRenderStage:
    """
    Image Render Stage - generates keyframe images for all shots.
    
    Responsibilities:
    1. Build image render inputs using ImageRenderInputBuilder
    2. Generate images in parallel using Image Provider
    3. Upload images to Object Storage
    4. Create Asset records
    5. Handle failures and retries
    
    Implements Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 11.1, 11.3, 12.1, 12.2, 12.3
    """
    
    def __init__(
        self,
        db: Session,
        image_provider: ImageProviderAdapter,
        storage_service: ObjectStorageService,
        input_builder: ImageRenderInputBuilder
    ):
        """
        Initialize the Image Render Stage.
        
        Args:
            db: Database session
            image_provider: Image provider adapter
            storage_service: Object storage service
            input_builder: Image render input builder
        """
        self.db = db
        self.image_provider = image_provider
        self.storage_service = storage_service
        self.input_builder = input_builder
        self.asset_repo = AssetRepository(db)
        self.shot_repo = ShotRepository(db)
        self.stage_task_repo = StageTaskRepository(db)
    
    async def execute(
        self,
        episode_id: UUID,
        project_id: UUID,
        stage_task_id: UUID,
        max_concurrent: int = 5,
        monitor: Optional["ProviderCallMonitor"] = None,
    ) -> StageExecutionResult:
        """
        Execute the Image Render Stage for an episode.
        
        Implements Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        
        Args:
            episode_id: Episode ID
            project_id: Project ID
            stage_task_id: StageTask ID for tracking
            max_concurrent: Maximum concurrent image generations
            
        Returns:
            StageExecutionResult: Execution result with metrics
        """
        start_time = time.time()
        
        # Create a monitor for this execution if not provided
        if monitor is None:
            monitor = ProviderCallMonitor()
        
        # Update stage task status to running
        self.stage_task_repo.update_status(
            stage_task_id,
            "running",
            started_at=datetime.utcnow()
        )
        
        try:
            # 1. Build inputs for all shots (Requirement 2.1)
            inputs = self.input_builder.build_inputs_for_episode(episode_id)
            
            if not inputs:
                # No shots to process
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.stage_task_repo.update_status(
                    stage_task_id,
                    "succeeded",
                    finished_at=datetime.utcnow()
                )
                
                return StageExecutionResult(
                    status="succeeded",
                    assets_created=0,
                    shots_processed=0,
                    shots_failed=0,
                    errors=[],
                    execution_time_ms=execution_time_ms,
                    metrics={}
                )
            
            # 2. Generate images in parallel (Requirement 11.1)
            results = await self._generate_images_parallel(
                inputs,
                max_concurrent,
                monitor,
            )
            
            # 3. Upload images and create assets (Requirement 2.3, 2.4)
            assets_created = await self._upload_and_create_assets(
                results,
                project_id,
                episode_id,
                stage_task_id
            )
            
            # 4. Calculate metrics
            execution_time_ms = int((time.time() - start_time) * 1000)
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]

            # Merge monitor metrics with stage-level metrics (Req 13.1, 13.2)
            monitor_metrics = monitor.to_metrics_dict()
            metrics = {
                "duration_ms": execution_time_ms,
                "provider_calls": monitor_metrics.get("provider_calls", len(results)),
                "success_count": monitor_metrics.get("success_count", len(successful_results)),
                "failure_count": monitor_metrics.get("failure_count", len(failed_results)),
                "estimated_cost_usd": monitor_metrics.get("estimated_cost_usd", len(successful_results) * 0.05),
                "image_calls": monitor_metrics.get("image_calls", len(successful_results)),
                "image_cost_usd": monitor_metrics.get("image_cost_usd", 0.0),
                "retry_count": sum(
                    (r.provider_metadata or {}).get('retry_count', 0)
                    for r in results
                ),
                "call_details": monitor_metrics.get("call_details", []),
                "errors": monitor_metrics.get("errors", []),
            }
            
            # 5. Determine final status
            if len(failed_results) == 0:
                final_status = "succeeded"
                task_status = "succeeded"
            elif len(successful_results) > 0:
                final_status = "partial_success"
                task_status = "succeeded"  # Partial success is still success
            else:
                final_status = "failed"
                task_status = "failed"
            
            # 6. Update stage task with metrics and final status
            self.stage_task_repo.update_metrics(
                stage_task_id,
                metrics=metrics,
                commit=False,
            )
            self.stage_task_repo.update_status(
                stage_task_id,
                task_status,
                finished_at=datetime.utcnow()
            )
            
            return StageExecutionResult(
                status=final_status,
                assets_created=assets_created,
                shots_processed=len(successful_results),
                shots_failed=len(failed_results),
                errors=[r.error for r in failed_results if r.error],
                execution_time_ms=execution_time_ms,
                metrics=metrics
            )
            
        except Exception as e:
            # Handle unexpected errors
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            self.stage_task_repo.update_status(
                stage_task_id,
                "failed",
                finished_at=datetime.utcnow(),
                error_message=str(e)
            )
            
            return StageExecutionResult(
                status="failed",
                assets_created=0,
                shots_processed=0,
                shots_failed=len(inputs) if inputs else 0,
                errors=[str(e)],
                execution_time_ms=execution_time_ms,
                metrics={}
            )
    
    async def _generate_images_parallel(
        self,
        inputs: List[ImageRenderInput],
        max_concurrent: int,
        monitor: "ProviderCallMonitor",
    ) -> List[ImageGenerationResult]:
        """
        Generate images in parallel with concurrency control.

        Implements Requirements: 11.1, 11.3

        Args:
            inputs: List of image render inputs
            max_concurrent: Maximum concurrent generations
            monitor: ProviderCallMonitor for recording calls

        Returns:
            List of ImageGenerationResult
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(input_data: ImageRenderInput):
            async with semaphore:
                return await self._generate_single_image_with_retry(input_data, monitor)

        # Create tasks for all inputs
        tasks = [generate_with_semaphore(inp) for inp in inputs]

        # Execute all tasks and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ImageGenerationResult(
                        success=False,
                        error=str(result),
                        shot_id=inputs[i].shot_id
                    )
                )
            else:
                processed_results.append(result)

        return processed_results
    
    async def _generate_single_image_with_retry(
        self,
        input_data: ImageRenderInput,
        monitor: "ProviderCallMonitor",
        max_retries: int = 3
    ) -> ImageGenerationResult:
        """
        Generate a single image with retry logic, recording each attempt.

        Implements Requirements: 12.1, 12.2, 12.3, 13.1

        Args:
            input_data: Image render input
            monitor: ProviderCallMonitor for recording calls
            max_retries: Maximum number of retries

        Returns:
            ImageGenerationResult
        """
        last_error = None
        retry_count = 0

        for attempt in range(max_retries):
            t0 = time.time()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.image_provider.generate_image(
                        prompt=input_data.prompt,
                        negative_prompt=input_data.negative_prompt,
                        width=input_data.resolution[0],
                        height=input_data.resolution[1],
                        style=input_data.visual_style,
                        shot_id=input_data.shot_id
                    )
                )

                duration_ms = int((time.time() - t0) * 1000)
                # Record successful call (Requirement 13.1)
                monitor.add_record(
                    provider_name=self.image_provider.provider_name,
                    operation="generate_image",
                    duration_ms=duration_ms,
                    success=result.success,
                    request_id=result.request_id,
                    error=result.error if not result.success else None,
                    extra={"shot_id": str(input_data.shot_id)},
                )

                if result.provider_metadata is None:
                    result.provider_metadata = {}
                result.provider_metadata['retry_count'] = retry_count
                return result

            except ProviderError as e:
                duration_ms = int((time.time() - t0) * 1000)
                last_error = e
                retry_count += 1

                # Record failed call (Requirement 13.1)
                monitor.add_record(
                    provider_name=self.image_provider.provider_name,
                    operation="generate_image",
                    duration_ms=duration_ms,
                    success=False,
                    request_id=e.request_id,
                    error=str(e),
                    extra={"shot_id": str(input_data.shot_id), "attempt": attempt},
                )

                if not e.is_retryable or attempt == max_retries - 1:
                    return ImageGenerationResult(
                        success=False,
                        error=str(e),
                        shot_id=input_data.shot_id,
                        request_id=e.request_id,
                        provider_metadata={'retry_count': retry_count}
                    )

                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

            except Exception as e:
                duration_ms = int((time.time() - t0) * 1000)
                monitor.add_record(
                    provider_name=self.image_provider.provider_name,
                    operation="generate_image",
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                    extra={"shot_id": str(input_data.shot_id)},
                )
                return ImageGenerationResult(
                    success=False,
                    error=f"Unexpected error: {str(e)}",
                    shot_id=input_data.shot_id,
                    provider_metadata={'retry_count': retry_count}
                )

        return ImageGenerationResult(
            success=False,
            error=f"Max retries exceeded: {last_error}",
            shot_id=input_data.shot_id,
            provider_metadata={'retry_count': retry_count}
        )
    
    async def _upload_and_create_assets(
        self,
        results: List[ImageGenerationResult],
        project_id: UUID,
        episode_id: UUID,
        stage_task_id: UUID
    ) -> int:
        """
        Upload generated images and create asset records.
        
        Implements Requirements: 2.3, 2.4, 9.1, 9.2
        
        Args:
            results: List of image generation results
            project_id: Project ID
            episode_id: Episode ID
            stage_task_id: StageTask ID
            
        Returns:
            Number of assets created
        """
        assets_created = 0
        
        for result in results:
            if not result.success or not result.image_data:
                continue
            
            try:
                # 1. Save image to temporary file
                temp_file = await self._save_to_temp_file(
                    result.image_data,
                    result.format or 'png'
                )
                
                try:
                    # 2. Generate storage key
                    storage_key = self.storage_service.generate_storage_key(
                        project_id=str(project_id),
                        episode_id=str(episode_id),
                        asset_type='keyframe',
                        file_extension=result.format or 'png'
                    )
                    
                    # 3. Upload to object storage
                    loop = asyncio.get_event_loop()
                    upload_result = await loop.run_in_executor(
                        None,
                        lambda: self.storage_service.upload_file(
                            file_path=temp_file,
                            storage_key=storage_key,
                            content_type=f'image/{result.format or "png"}',
                            metadata={
                                'shot_id': str(result.shot_id),
                                'stage_task_id': str(stage_task_id)
                            }
                        )
                    )
                    
                    # 4. Create asset record
                    asset = self.asset_repo.create_asset(
                        project_id=project_id,
                        episode_id=episode_id,
                        shot_id=result.shot_id,
                        stage_task_id=stage_task_id,
                        asset_type='keyframe',
                        storage_key=upload_result.storage_key,
                        mime_type=f'image/{result.format or "png"}',
                        size_bytes=upload_result.size_bytes,
                        width=result.width,
                        height=result.height,
                        is_selected=True,  # First keyframe is selected by default
                        metadata_jsonb=result.provider_metadata or {}
                    )
                    
                    assets_created += 1
                    
                finally:
                    # 5. Clean up temporary file
                    await self._cleanup_temp_file(temp_file)
                    
            except Exception as e:
                # Log error but continue processing other results
                print(f"Error uploading asset for shot {result.shot_id}: {e}")
                continue
        
        return assets_created
    
    async def _save_to_temp_file(
        self,
        image_data: bytes,
        format: str
    ) -> str:
        """
        Save image data to a temporary file.
        
        Args:
            image_data: Binary image data
            format: Image format (png, jpeg, etc.)
            
        Returns:
            Path to temporary file
        """
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix=f'.{format}')
        
        try:
            # Write data
            os.write(fd, image_data)
        finally:
            os.close(fd)
        
        return temp_path
    
    async def _cleanup_temp_file(self, file_path: str) -> None:
        """
        Clean up a temporary file.
        
        Args:
            file_path: Path to temporary file
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Log but don't fail
            print(f"Warning: Failed to cleanup temp file {file_path}: {e}")
