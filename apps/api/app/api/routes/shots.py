"""
Shot API routes.

Implements Requirements:
- 6.1: Query episode shots
- 9.1: Return complete shot information
- 9.2: Include visual_constraints
- 9.3: Support version parameter
- 9.4: Include status and version
- 9.5: Sort by scene_no and shot_no
- 8.1: Select primary asset for a shot
- 8.2: Get candidate assets for a shot
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_store
from app.schemas.common import SuccessEnvelope
from app.schemas.shot import ShotResponse, ShotListResponse, UpdateShotRequest, AssetResponse, AssetListResponse, SelectAssetRequest
from app.services.store import DatabaseStore
from app.services.shot_service import ShotService, ShotValidationError
from app.services.asset_service import AssetService

router = APIRouter(prefix="/api", tags=["shots"])


@router.get("/episodes/{episode_id}/shots", response_model=SuccessEnvelope)
def list_episode_shots(
    episode_id: UUID,
    version: Optional[int] = Query(None, description="Specific version to query. If not provided, returns latest version."),
    store: DatabaseStore = Depends(get_store)
) -> SuccessEnvelope:
    """
    Get all shots for an episode.
    
    Implements Requirements:
    - 6.1: Query Episode's all shots
    - 9.1: Return complete shot list
    - 9.2: Include visual_constraints
    - 9.3: Support version parameter for historical versions
    - 9.5: Sort by scene_no and shot_no
    
    Args:
        episode_id: UUID of the episode
        version: Optional version number. If not provided, returns latest version.
        store: Database store dependency
        
    Returns:
        SuccessEnvelope containing ShotListResponse with all shots
        
    Raises:
        HTTPException 404: If episode not found or no shots exist
    """
    # Verify episode exists
    episode = store.get_episode(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Get shots based on version parameter
    if version is not None:
        # Query specific version
        from app.repositories.shot_repository import ShotRepository
        shot_repo = ShotRepository(store.db)
        
        # Get all shots for this episode and version
        from sqlalchemy import select
        from app.db.models import ShotModel
        stmt = (
            select(ShotModel)
            .where(
                ShotModel.episode_id == episode_id,
                ShotModel.version == version
            )
            .order_by(ShotModel.scene_no.asc(), ShotModel.shot_no.asc())
        )
        shots = list(store.db.scalars(stmt).all())
        
        if not shots:
            raise HTTPException(
                status_code=404,
                detail=f"No shots found for episode {episode_id} version {version}"
            )
        
        latest_version = shot_repo.latest_version_for_episode(episode_id)
    else:
        # Query latest version (default)
        from app.repositories.shot_repository import ShotRepository
        shot_repo = ShotRepository(store.db)
        shots = shot_repo.list_current_for_episode(episode_id)
        
        if not shots:
            raise HTTPException(
                status_code=404,
                detail=f"No shots found for episode {episode_id}"
            )
        
        latest_version = shot_repo.latest_version_for_episode(episode_id)
    
    # Convert to response models
    shot_responses = [ShotResponse.model_validate(shot, from_attributes=True) for shot in shots]
    
    response_data = ShotListResponse(
        shots=shot_responses,
        total_count=len(shot_responses),
        episode_id=episode_id,
        latest_version=latest_version
    )
    
    return SuccessEnvelope(data=response_data)


@router.get("/shots/{shot_id}", response_model=SuccessEnvelope)
def get_shot_by_id(
    shot_id: UUID,
    version: Optional[int] = Query(None, description="Specific version to query. If not provided, returns the shot regardless of version."),
    store: DatabaseStore = Depends(get_store)
) -> SuccessEnvelope:
    """
    Get a single shot by ID.
    
    Implements Requirements:
    - 6.1: Query single shot details
    - 9.2: Return complete information including visual_constraints
    - 9.3: Support version parameter
    - 9.4: Include status and version
    
    Args:
        shot_id: UUID of the shot
        version: Optional version number
        store: Database store dependency
        
    Returns:
        SuccessEnvelope containing ShotResponse
        
    Raises:
        HTTPException 404: If shot not found
    """
    from app.repositories.shot_repository import ShotRepository
    shot_repo = ShotRepository(store.db)
    
    if version is not None:
        # Query specific version
        shot = shot_repo.get_by_id_and_version(shot_id, version)
        if not shot:
            raise HTTPException(
                status_code=404,
                detail=f"Shot {shot_id} version {version} not found"
            )
    else:
        # Query by ID (any version)
        shot = shot_repo.get_by_id(shot_id)
        if not shot:
            raise HTTPException(status_code=404, detail=f"Shot {shot_id} not found")
    
    # Convert to response model
    shot_response = ShotResponse.model_validate(shot, from_attributes=True)
    
    return SuccessEnvelope(data=shot_response)


@router.put("/shots/{shot_id}", response_model=SuccessEnvelope)
def update_shot(
    shot_id: UUID,
    payload: UpdateShotRequest,
    store: DatabaseStore = Depends(get_store)
) -> SuccessEnvelope:
    """
    Update a shot's visual_constraints by creating a new version.
    
    Implements Requirements:
    - 7.1: Support modifying visual_constraints_jsonb
    - 7.2: Create new version instead of overwriting
    - 7.5: Validate visual_constraints Schema
    
    Args:
        shot_id: UUID of the shot to update
        payload: UpdateShotRequest with new visual_constraints
        store: Database store dependency
        
    Returns:
        SuccessEnvelope containing the updated ShotResponse (new version)
        
    Raises:
        HTTPException 404: If shot not found
        HTTPException 400: If visual_constraints validation fails
    """
    shot_service = ShotService(store.db)
    
    try:
        updated_shot = shot_service.update_shot_visual_constraints(
            shot_id=shot_id,
            new_visual_constraints=payload.visual_constraints_jsonb,
            user_id=payload.user_id
        )
        
        # Convert to response model
        shot_response = ShotResponse.model_validate(updated_shot, from_attributes=True)
        
        return SuccessEnvelope(data=shot_response)
        
    except ValueError as e:
        # Shot not found
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ShotValidationError as e:
        # Validation error
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}") from e



@router.get("/shots/{shot_id}/assets", response_model=SuccessEnvelope)
def get_shot_assets(
    shot_id: UUID,
    asset_type: Optional[str] = Query(None, description="Filter by asset type (e.g., 'keyframe', 'audio')"),
    store: DatabaseStore = Depends(get_store)
) -> SuccessEnvelope:
    """
    Get all candidate assets for a shot.
    
    Implements Requirements:
    - 8.1: Get candidate assets for a shot
    - 8.2: Display asset list with selection status
    
    Args:
        shot_id: UUID of the shot
        asset_type: Optional filter by asset type
        store: Database store dependency
        
    Returns:
        SuccessEnvelope containing AssetListResponse with all candidate assets
        
    Raises:
        HTTPException 404: If shot not found
    """
    # Verify shot exists
    from app.repositories.shot_repository import ShotRepository
    shot_repo = ShotRepository(store.db)
    shot = shot_repo.get_by_id(shot_id)
    
    if not shot:
        raise HTTPException(status_code=404, detail=f"Shot {shot_id} not found")
    
    # Get candidate assets
    asset_service = AssetService(store.db)
    assets = asset_service.get_candidate_assets(
        shot_id=shot_id,
        asset_type=asset_type
    )
    
    # Convert to response models
    asset_responses = [AssetResponse.model_validate(asset, from_attributes=True) for asset in assets]
    
    response_data = AssetListResponse(
        assets=asset_responses,
        total_count=len(asset_responses),
        shot_id=shot_id
    )
    
    return SuccessEnvelope(data=response_data)


@router.post("/shots/{shot_id}/assets/{asset_id}/select", response_model=SuccessEnvelope)
def select_primary_asset(
    shot_id: UUID,
    asset_id: UUID,
    payload: SelectAssetRequest,
    store: DatabaseStore = Depends(get_store)
) -> SuccessEnvelope:
    """
    Select a primary asset for a shot.
    
    Implements Requirements:
    - 8.1: Select primary asset for a shot
    - 8.2: Ensure only one primary asset per shot
    - 8.4: Record selection history
    
    Args:
        shot_id: UUID of the shot
        asset_id: UUID of the asset to select as primary
        payload: SelectAssetRequest with optional metadata
        store: Database store dependency
        
    Returns:
        SuccessEnvelope containing the updated AssetResponse
        
    Raises:
        HTTPException 404: If shot or asset not found
        HTTPException 400: If asset doesn't belong to the shot
    """
    # Verify shot exists
    from app.repositories.shot_repository import ShotRepository
    shot_repo = ShotRepository(store.db)
    shot = shot_repo.get_by_id(shot_id)
    
    if not shot:
        raise HTTPException(status_code=404, detail=f"Shot {shot_id} not found")
    
    # Select primary asset
    asset_service = AssetService(store.db)
    
    try:
        updated_asset = asset_service.select_primary_asset(
            shot_id=shot_id,
            asset_id=asset_id,
            asset_type=payload.asset_type,
            selected_by=payload.selected_by or "user"
        )
        
        # Commit the transaction
        store.db.commit()
        
        # Convert to response model
        asset_response = AssetResponse.model_validate(updated_asset, from_attributes=True)
        
        return SuccessEnvelope(data=asset_response)
        
    except ValueError as e:
        # Asset not found or validation error
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        store.db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to select asset: {str(e)}") from e



@router.get("/assets/{asset_id}/selection-history", response_model=SuccessEnvelope)
def get_asset_selection_history(
    asset_id: UUID,
    store: DatabaseStore = Depends(get_store)
) -> SuccessEnvelope:
    """
    Get selection history for an asset.
    
    Implements Requirements:
    - 8.4: Query selection history
    
    Args:
        asset_id: UUID of the asset
        store: Database store dependency
        
    Returns:
        SuccessEnvelope containing selection history
        
    Raises:
        HTTPException 404: If asset not found
    """
    asset_service = AssetService(store.db)
    
    try:
        history = asset_service.get_selection_history(asset_id)
        
        return SuccessEnvelope(data={
            "asset_id": asset_id,
            "selection_history": history
        })
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
