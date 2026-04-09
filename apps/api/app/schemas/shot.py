"""
Shot schemas for API requests and responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class ShotResponse(BaseModel):
    """
    Response schema for Shot data.
    
    Implements Requirements:
    - 6.1: Display shot details in shot cards
    - 9.1: Return complete shot list in workspace
    - 9.2: Include visual_constraints summary
    - 9.4: Include shot status and version
    """
    id: UUID
    project_id: UUID
    episode_id: UUID
    stage_task_id: Optional[UUID] = None
    
    # Shot identification
    scene_no: int
    shot_no: int
    shot_code: str
    status: str
    
    # Duration and camera parameters
    duration_ms: int
    camera_size: Optional[str] = None
    camera_angle: Optional[str] = None
    movement_type: Optional[str] = None
    
    # Content information
    characters_jsonb: List[str] = Field(default_factory=list)
    action_text: Optional[str] = None
    dialogue_text: Optional[str] = None
    
    # Visual constraints (complete structure)
    visual_constraints_jsonb: Dict[str, Any] = Field(default_factory=dict)
    
    # Version control
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ShotListResponse(BaseModel):
    """
    Response schema for list of shots.
    
    Implements Requirements:
    - 9.1: Return complete shot list
    - 9.5: Sort by scene_no and shot_no
    """
    shots: List[ShotResponse]
    total_count: int
    episode_id: UUID
    latest_version: int


class UpdateShotRequest(BaseModel):
    """
    Request schema for updating a shot's visual_constraints.
    
    Implements Requirements:
    - 7.1: Support modifying visual_constraints_jsonb
    - 7.5: Validate visual_constraints Schema
    """
    visual_constraints_jsonb: Dict[str, Any] = Field(
        ...,
        description="Updated visual constraints. Must include render_prompt, style_keywords, composition, and character_refs."
    )
    user_id: Optional[UUID] = Field(
        None,
        description="ID of the user making the edit (for audit trail)"
    )



class AssetResponse(BaseModel):
    """
    Response schema for Asset data.
    
    Implements Requirements:
    - 8.1: Display asset details
    - 8.2: Include selection status
    - 8.4: Include selection metadata
    """
    id: UUID
    project_id: UUID
    episode_id: Optional[UUID] = None
    stage_task_id: Optional[UUID] = None
    shot_id: Optional[UUID] = None
    
    # Asset information
    asset_type: str
    storage_key: str
    mime_type: str
    size_bytes: int
    
    # Media metadata
    duration_ms: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    checksum_sha256: Optional[str] = None
    quality_score: Optional[float] = None
    
    # Selection status
    is_selected: bool
    version: int
    
    # Metadata including selection history
    metadata_jsonb: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """
    Response schema for list of assets.
    
    Implements Requirements:
    - 8.1: Return complete asset list for a shot
    """
    assets: List[AssetResponse]
    total_count: int
    shot_id: UUID


class SelectAssetRequest(BaseModel):
    """
    Request schema for selecting a primary asset.
    
    Implements Requirements:
    - 8.1: Select primary asset
    - 8.4: Record selection source
    """
    asset_type: Optional[str] = Field(
        None,
        description="Optional filter by asset type to ensure uniqueness within type"
    )
    selected_by: Optional[str] = Field(
        None,
        description="Identifier of who made the selection (user ID or 'system')"
    )
