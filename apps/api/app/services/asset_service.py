"""
Asset Service

Provides business logic for asset management, including primary asset selection.

Requirements:
- 10.2: Select primary asset for a shot
- 10.3: Ensure only one primary asset per shot
- 10.4: Record selection operation
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from app.repositories.asset_repository import AssetRepository
from app.db.models import AssetModel

logger = logging.getLogger(__name__)


class AssetService:
    """Service for managing assets and primary asset selection."""
    
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
    
    def select_primary_asset(
        self,
        shot_id: UUID,
        asset_id: UUID,
        asset_type: Optional[str] = None,
        selected_by: Optional[str] = None
    ) -> AssetModel:
        """
        Select a primary asset for a shot.
        
        This ensures only one asset is marked as primary for the given shot
        and asset type combination.
        
        Requirements: 10.2, 10.3, 10.4
        
        Args:
            shot_id: Shot UUID
            asset_id: Asset UUID to mark as primary
            asset_type: Optional filter by asset type (e.g., 'keyframe')
            selected_by: Optional identifier of who made the selection
            
        Returns:
            Updated AssetModel instance
            
        Raises:
            ValueError: If asset not found or validation fails
        """
        logger.info(
            f"Selecting primary asset: shot_id={shot_id}, "
            f"asset_id={asset_id}, asset_type={asset_type}, "
            f"selected_by={selected_by}"
        )
        
        try:
            # Use repository to update selection
            asset = self.asset_repo.update_selected_asset(
                shot_id=shot_id,
                asset_id=asset_id,
                asset_type=asset_type
            )
            
            # Record selection metadata
            if not asset.metadata_jsonb:
                asset.metadata_jsonb = {}
            
            asset.metadata_jsonb["selection_history"] = asset.metadata_jsonb.get(
                "selection_history", []
            )
            
            asset.metadata_jsonb["selection_history"].append({
                "selected_at": datetime.utcnow().isoformat(),
                "selected_by": selected_by or "system",
            })
            
            # Keep only last 10 selection history entries
            if len(asset.metadata_jsonb["selection_history"]) > 10:
                asset.metadata_jsonb["selection_history"] = (
                    asset.metadata_jsonb["selection_history"][-10:]
                )
            
            self.db.flush()
            self.db.refresh(asset)
            
            logger.info(
                f"Successfully selected primary asset {asset_id} for shot {shot_id}"
            )
            
            return asset
            
        except ValueError as e:
            logger.error(f"Failed to select primary asset: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error selecting primary asset: {e}")
            raise
    
    def get_primary_asset(
        self,
        shot_id: UUID,
        asset_type: Optional[str] = None
    ) -> Optional[AssetModel]:
        """
        Get the primary asset for a shot.
        
        Args:
            shot_id: Shot UUID
            asset_type: Optional filter by asset type
            
        Returns:
            AssetModel if found, None otherwise
        """
        return self.asset_repo.get_selected_asset_by_shot(
            shot_id=shot_id,
            asset_type=asset_type
        )
    
    def get_candidate_assets(
        self,
        shot_id: UUID,
        asset_type: Optional[str] = None
    ) -> List[AssetModel]:
        """
        Get all candidate assets for a shot.
        
        Args:
            shot_id: Shot UUID
            asset_type: Optional filter by asset type
            
        Returns:
            List of AssetModel instances
        """
        return self.asset_repo.get_assets_by_shot(
            shot_id=shot_id,
            asset_type=asset_type
        )
    
    def create_asset(
        self,
        project_id: UUID,
        episode_id: UUID,
        asset_type: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int = 0,
        shot_id: Optional[UUID] = None,
        stage_task_id: Optional[UUID] = None,
        duration_ms: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        checksum_sha256: Optional[str] = None,
        quality_score: Optional[float] = None,
        is_selected: bool = False,
        version: int = 1,
        metadata_jsonb: Optional[dict] = None,
    ) -> AssetModel:
        """
        Create a new asset.
        
        Args:
            project_id: Project UUID
            episode_id: Episode UUID
            asset_type: Type of asset
            storage_key: Storage location key
            mime_type: MIME type
            size_bytes: Size in bytes
            shot_id: Optional Shot UUID
            stage_task_id: Optional StageTask UUID
            duration_ms: Optional duration
            width: Optional width
            height: Optional height
            checksum_sha256: Optional checksum
            quality_score: Optional quality score
            is_selected: Whether this is the primary asset
            version: Version number
            metadata_jsonb: Optional metadata
            
        Returns:
            Created AssetModel instance
        """
        logger.info(
            f"Creating asset: type={asset_type}, shot_id={shot_id}, "
            f"is_selected={is_selected}"
        )
        
        asset = self.asset_repo.create_asset(
            project_id=project_id,
            episode_id=episode_id,
            asset_type=asset_type,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            shot_id=shot_id,
            stage_task_id=stage_task_id,
            duration_ms=duration_ms,
            width=width,
            height=height,
            checksum_sha256=checksum_sha256,
            quality_score=quality_score,
            is_selected=is_selected,
            version=version,
            metadata_jsonb=metadata_jsonb,
        )
        
        logger.info(f"Successfully created asset {asset.id}")
        
        return asset
