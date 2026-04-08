from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import AssetModel


class AssetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_episode(self, episode_id) -> List[AssetModel]:
        stmt = (
            select(AssetModel)
            .where(AssetModel.episode_id == episode_id)
            .order_by(AssetModel.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_selected_for_episode(self, episode_id) -> List[AssetModel]:
        stmt = (
            select(AssetModel)
            .where(
                AssetModel.episode_id == episode_id,
                AssetModel.is_selected.is_(True),
            )
            .order_by(AssetModel.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

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
        Create a new asset record.
        
        Requirements: 8.1, 8.4, 8.5, 10.2, 10.3
        
        Args:
            project_id: Project UUID
            episode_id: Episode UUID
            asset_type: Type of asset (keyframe, audio, subtitle, etc.)
            storage_key: Storage location key
            mime_type: MIME type of the asset
            size_bytes: Size in bytes
            shot_id: Optional Shot UUID for shot-level assets
            stage_task_id: Optional StageTask UUID
            duration_ms: Optional duration in milliseconds
            width: Optional width in pixels
            height: Optional height in pixels
            checksum_sha256: Optional SHA256 checksum
            quality_score: Optional quality score (0-100)
            is_selected: Whether this is the selected/primary asset
            version: Version number
            metadata_jsonb: Optional metadata dictionary
            
        Returns:
            Created AssetModel instance
        """
        asset = AssetModel(
            project_id=project_id,
            episode_id=episode_id,
            shot_id=shot_id,
            stage_task_id=stage_task_id,
            asset_type=asset_type,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            duration_ms=duration_ms,
            width=width,
            height=height,
            checksum_sha256=checksum_sha256,
            quality_score=quality_score,
            is_selected=is_selected,
            version=version,
            metadata_jsonb=metadata_jsonb or {},
        )
        
        self.db.add(asset)
        self.db.flush()
        self.db.refresh(asset)
        
        return asset

    def get_assets_by_shot(
        self,
        shot_id: UUID,
        asset_type: Optional[str] = None
    ) -> List[AssetModel]:
        """
        Query all assets for a specific shot.
        
        Requirements: 8.4
        
        Args:
            shot_id: Shot UUID
            asset_type: Optional filter by asset type
            
        Returns:
            List of AssetModel instances ordered by created_at descending
        """
        stmt = (
            select(AssetModel)
            .where(AssetModel.shot_id == shot_id)
        )
        
        if asset_type:
            stmt = stmt.where(AssetModel.asset_type == asset_type)
        
        stmt = stmt.order_by(AssetModel.created_at.desc())
        
        return list(self.db.scalars(stmt).all())

    def get_selected_asset_by_shot(
        self,
        shot_id: UUID,
        asset_type: Optional[str] = None
    ) -> Optional[AssetModel]:
        """
        Query the selected/primary asset for a specific shot.
        
        Requirements: 8.5, 10.2
        
        Args:
            shot_id: Shot UUID
            asset_type: Optional filter by asset type
            
        Returns:
            AssetModel instance if found, None otherwise
        """
        stmt = (
            select(AssetModel)
            .where(
                AssetModel.shot_id == shot_id,
                AssetModel.is_selected.is_(True)
            )
        )
        
        if asset_type:
            stmt = stmt.where(AssetModel.asset_type == asset_type)
        
        stmt = stmt.order_by(AssetModel.created_at.desc())
        
        return self.db.scalars(stmt).first()

    def update_selected_asset(
        self,
        shot_id: UUID,
        asset_id: UUID,
        asset_type: Optional[str] = None
    ) -> AssetModel:
        """
        Update the selected/primary asset for a shot.
        
        This ensures only one asset is marked as selected for a given shot
        (and optionally asset_type).
        
        Requirements: 10.2, 10.3
        
        Args:
            shot_id: Shot UUID
            asset_id: Asset UUID to mark as selected
            asset_type: Optional filter by asset type
            
        Returns:
            Updated AssetModel instance
            
        Raises:
            ValueError: If asset not found or doesn't belong to the shot
        """
        # First, verify the asset exists and belongs to the shot
        asset = self.db.get(AssetModel, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        if asset.shot_id != shot_id:
            raise ValueError(f"Asset {asset_id} does not belong to shot {shot_id}")
        
        if asset_type and asset.asset_type != asset_type:
            raise ValueError(f"Asset {asset_id} is not of type {asset_type}")
        
        # Unselect all other assets for this shot (and optionally asset_type)
        stmt = (
            update(AssetModel)
            .where(
                AssetModel.shot_id == shot_id,
                AssetModel.id != asset_id,
                AssetModel.is_selected.is_(True)
            )
            .values(is_selected=False)
        )
        
        if asset_type:
            stmt = stmt.where(AssetModel.asset_type == asset_type)
        
        self.db.execute(stmt)
        
        # Select the target asset
        asset.is_selected = True
        self.db.flush()
        self.db.refresh(asset)
        
        return asset
