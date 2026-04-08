"""
Shot service for business logic.

Implements Requirements:
- 7.1: Edit shot visual_constraints
- 7.2: Create new version instead of overwriting
- 7.5: Validate visual_constraints Schema
"""
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.models import ShotModel
from app.repositories.shot_repository import ShotRepository


class ShotValidationError(Exception):
    """Raised when shot visual_constraints validation fails."""
    pass


class ShotService:
    """Service for shot-related business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.shot_repo = ShotRepository(db)
    
    def update_shot_visual_constraints(
        self,
        shot_id: UUID,
        new_visual_constraints: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> ShotModel:
        """
        Update a shot's visual_constraints by creating a new version.
        
        Implements Requirements:
        - 7.1: Support modifying visual_constraints_jsonb
        - 7.2: Create new version instead of overwriting
        - 7.5: Validate visual_constraints Schema
        
        Args:
            shot_id: UUID of the shot to update
            new_visual_constraints: New visual constraints data
            user_id: Optional user ID for audit trail
            
        Returns:
            ShotModel: The newly created shot version
            
        Raises:
            ValueError: If shot not found
            ShotValidationError: If visual_constraints validation fails
        """
        # Get the current shot
        current_shot = self.shot_repo.get_by_id(shot_id)
        if not current_shot:
            raise ValueError(f"Shot {shot_id} not found")
        
        # Validate visual_constraints schema
        self._validate_visual_constraints(new_visual_constraints)
        
        # Create new version
        new_version = current_shot.version + 1
        
        # Create new shot record with incremented version
        new_shot_data = {
            "id": current_shot.id,  # Keep same ID
            "project_id": current_shot.project_id,
            "episode_id": current_shot.episode_id,
            "stage_task_id": current_shot.stage_task_id,
            "scene_no": current_shot.scene_no,
            "shot_no": current_shot.shot_no,
            "shot_code": current_shot.shot_code,
            "status": current_shot.status,
            "duration_ms": current_shot.duration_ms,
            "camera_size": current_shot.camera_size,
            "camera_angle": current_shot.camera_angle,
            "movement_type": current_shot.movement_type,
            "characters_jsonb": current_shot.characters_jsonb,
            "action_text": current_shot.action_text,
            "dialogue_text": current_shot.dialogue_text,
            "visual_constraints_jsonb": new_visual_constraints,  # Updated field
            "version": new_version  # Incremented version
        }
        
        # Create the new version
        new_shot = self.shot_repo.create_shot(new_shot_data, commit=True)
        
        return new_shot
    
    def _validate_visual_constraints(self, visual_constraints: Dict[str, Any]) -> None:
        """
        Validate visual_constraints schema.
        
        Implements Requirement 7.5: Validate visual_constraints Schema
        
        Required fields:
        - render_prompt: str (non-empty)
        - style_keywords: list
        - composition: str
        - character_refs: list
        
        Args:
            visual_constraints: Visual constraints to validate
            
        Raises:
            ShotValidationError: If validation fails
        """
        # Check required fields
        required_fields = ["render_prompt", "style_keywords", "composition", "character_refs"]
        for field in required_fields:
            if field not in visual_constraints:
                raise ShotValidationError(f"Missing required field: {field}")
        
        # Validate render_prompt
        render_prompt = visual_constraints.get("render_prompt")
        if not isinstance(render_prompt, str) or len(render_prompt.strip()) == 0:
            raise ShotValidationError("render_prompt must be a non-empty string")
        
        # Validate style_keywords
        style_keywords = visual_constraints.get("style_keywords")
        if not isinstance(style_keywords, list):
            raise ShotValidationError("style_keywords must be a list")
        
        # Validate composition
        composition = visual_constraints.get("composition")
        if not isinstance(composition, str):
            raise ShotValidationError("composition must be a string")
        
        # Validate character_refs
        character_refs = visual_constraints.get("character_refs")
        if not isinstance(character_refs, list):
            raise ShotValidationError("character_refs must be a list")
        
        # Validate all character_refs are strings
        for ref in character_refs:
            if not isinstance(ref, str):
                raise ShotValidationError("All character_refs must be strings")
