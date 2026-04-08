"""
Image Render Input Builder Service

Constructs input parameters for the image_render Stage from Shot visual_constraints
and character_profile documents.

Implements Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 12.1, 12.2, 12.3, 12.4, 12.5
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.shot_repository import ShotRepository
from app.repositories.document_repository import DocumentRepository
from app.db.models import ShotModel


@dataclass
class ImageRenderInput:
    """
    Input parameters for image_render Stage.
    
    Implements Requirements: 5.1, 5.2, 5.3, 5.4
    """
    
    # Identifiers
    shot_id: UUID
    episode_id: UUID
    
    # Core parameters
    prompt: str  # Complete render prompt (merged with visual_anchor)
    negative_prompt: str  # Negative prompt
    
    # Style parameters
    style_keywords: List[str]  # Style keywords
    visual_style: str  # Overall visual style
    
    # Composition parameters
    composition: str  # Shot composition
    camera_size: str  # Camera size (close-up, medium, wide)
    camera_angle: str  # Camera angle (eye-level, low, high)
    
    # Character parameters
    character_refs: List[str]  # Character references
    character_anchors: Dict[str, str]  # {character_name: visual_anchor}
    
    # Technical parameters
    aspect_ratio: str  # Aspect ratio, e.g., "9:16"
    resolution: Tuple[int, int]  # Resolution, e.g., (1080, 1920)
    
    # Metadata
    scene_no: int
    shot_no: int
    shot_code: str
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        # Validate prompt is not empty (Requirement 5.1)
        if not self.prompt or not self.prompt.strip():
            raise ValueError("prompt cannot be empty")
        
        # Validate style_keywords is a list (Requirement 5.3)
        if not isinstance(self.style_keywords, list):
            raise ValueError("style_keywords must be a list")
        
        # Validate character_refs is a list (Requirement 5.2)
        if not isinstance(self.character_refs, list):
            raise ValueError("character_refs must be a list")
        
        # Validate character_anchors is a dict (Requirement 5.2)
        if not isinstance(self.character_anchors, dict):
            raise ValueError("character_anchors must be a dict")
        
        # Validate resolution is a tuple of two integers
        if not isinstance(self.resolution, tuple) or len(self.resolution) != 2:
            raise ValueError("resolution must be a tuple of (width, height)")
        
        # Validate scene_no and shot_no are positive
        if self.scene_no <= 0:
            raise ValueError("scene_no must be positive")
        if self.shot_no <= 0:
            raise ValueError("shot_no must be positive")
    
    def to_dict(self) -> Dict:
        """
        Serialize to dictionary.
        
        Converts UUID and tuple types to serializable formats.
        """
        data = asdict(self)
        # Convert UUIDs to strings
        data['shot_id'] = str(self.shot_id)
        data['episode_id'] = str(self.episode_id)
        # Resolution is already a tuple, which is JSON-serializable as array
        return data


class ImageRenderInputBuilder:
    """
    Constructs image_render Stage input parameters.
    
    Responsibilities:
    1. Load Shot visual_constraints
    2. Load associated character_profile
    3. Merge render_prompt with visual_anchor
    4. Assemble complete image generation parameters
    
    Implements Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 12.1, 12.2, 12.3, 12.4, 12.5
    """
    
    # Default technical parameters
    DEFAULT_ASPECT_RATIO = "9:16"
    DEFAULT_RESOLUTION = (1080, 1920)
    DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed"
    DEFAULT_VISUAL_STYLE = "anime"
    
    def __init__(self, db: Session):
        self.db = db
        self.shot_repo = ShotRepository(db)
        self.document_repo = DocumentRepository(db)
    
    def build_input_for_shot(
        self,
        shot_id: UUID,
        episode_id: UUID
    ) -> ImageRenderInput:
        """
        Build image_render input for a single Shot.
        
        Implements Requirements: 5.1, 5.2, 5.3, 5.4, 12.1, 12.2, 12.3, 12.4
        
        Args:
            shot_id: ID of the Shot
            episode_id: ID of the Episode
            
        Returns:
            ImageRenderInput with complete parameters
            
        Raises:
            ValueError: If Shot not found or required data missing
        """
        # Load Shot record
        shot = self._get_shot_by_id(shot_id)
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")
        
        if shot.episode_id != episode_id:
            raise ValueError(f"Shot {shot_id} does not belong to Episode {episode_id}")
        
        # Load character_profile document (Requirement 12.2)
        character_profile = self._load_character_profile(episode_id)
        
        # Load visual_spec document for visual_style
        visual_spec = self._load_visual_spec(episode_id)
        
        # Extract visual_constraints from Shot (Requirement 5.1)
        visual_constraints = shot.visual_constraints_jsonb or {}
        render_prompt = visual_constraints.get("render_prompt", "")
        style_keywords = visual_constraints.get("style_keywords", [])
        composition = visual_constraints.get("composition", "")
        character_refs = visual_constraints.get("character_refs", [])
        
        # Validate render_prompt is not empty
        if not render_prompt or not render_prompt.strip():
            raise ValueError(f"Shot {shot_id} has empty render_prompt")
        
        # Merge render_prompt with visual_anchors (Requirement 5.2, 12.3)
        enhanced_prompt, character_anchors = self._merge_prompt_with_anchors(
            render_prompt,
            character_refs,
            character_profile
        )
        
        # Get visual_style from visual_spec (Requirement 5.3)
        visual_style = self.DEFAULT_VISUAL_STYLE
        if visual_spec:
            visual_style = visual_spec.content_jsonb.get("visual_style", self.DEFAULT_VISUAL_STYLE)
        
        # Construct ImageRenderInput (Requirement 5.4)
        return ImageRenderInput(
            shot_id=shot.id,
            episode_id=shot.episode_id,
            prompt=enhanced_prompt,
            negative_prompt=self.DEFAULT_NEGATIVE_PROMPT,
            style_keywords=style_keywords,
            visual_style=visual_style,
            composition=composition,
            camera_size=shot.camera_size or "medium",
            camera_angle=shot.camera_angle or "eye-level",
            character_refs=character_refs,
            character_anchors=character_anchors,
            aspect_ratio=self.DEFAULT_ASPECT_RATIO,
            resolution=self.DEFAULT_RESOLUTION,
            scene_no=shot.scene_no,
            shot_no=shot.shot_no,
            shot_code=shot.shot_code
        )
    
    def build_inputs_for_episode(
        self,
        episode_id: UUID
    ) -> List[ImageRenderInput]:
        """
        Build image_render inputs for all Shots in an Episode.
        
        Implements Requirements: 5.5, 12.5
        
        Args:
            episode_id: ID of the Episode
            
        Returns:
            List of ImageRenderInput for all Shots
        """
        # Load all current Shots for the Episode
        shots = self.shot_repo.list_current_for_episode(episode_id)
        
        if not shots:
            return []
        
        # Load character_profile once for all Shots (optimization)
        character_profile = self._load_character_profile(episode_id)
        
        # Load visual_spec once for all Shots (optimization)
        visual_spec = self._load_visual_spec(episode_id)
        
        # Build inputs for each Shot
        inputs = []
        for shot in shots:
            try:
                # Extract visual_constraints
                visual_constraints = shot.visual_constraints_jsonb or {}
                render_prompt = visual_constraints.get("render_prompt", "")
                style_keywords = visual_constraints.get("style_keywords", [])
                composition = visual_constraints.get("composition", "")
                character_refs = visual_constraints.get("character_refs", [])
                
                # Skip Shots with empty render_prompt
                if not render_prompt or not render_prompt.strip():
                    continue
                
                # Merge render_prompt with visual_anchors
                enhanced_prompt, character_anchors = self._merge_prompt_with_anchors(
                    render_prompt,
                    character_refs,
                    character_profile
                )
                
                # Get visual_style
                visual_style = self.DEFAULT_VISUAL_STYLE
                if visual_spec:
                    visual_style = visual_spec.content_jsonb.get("visual_style", self.DEFAULT_VISUAL_STYLE)
                
                # Construct ImageRenderInput
                input_obj = ImageRenderInput(
                    shot_id=shot.id,
                    episode_id=shot.episode_id,
                    prompt=enhanced_prompt,
                    negative_prompt=self.DEFAULT_NEGATIVE_PROMPT,
                    style_keywords=style_keywords,
                    visual_style=visual_style,
                    composition=composition,
                    camera_size=shot.camera_size or "medium",
                    camera_angle=shot.camera_angle or "eye-level",
                    character_refs=character_refs,
                    character_anchors=character_anchors,
                    aspect_ratio=self.DEFAULT_ASPECT_RATIO,
                    resolution=self.DEFAULT_RESOLUTION,
                    scene_no=shot.scene_no,
                    shot_no=shot.shot_no,
                    shot_code=shot.shot_code
                )
                
                inputs.append(input_obj)
            except Exception as e:
                # Log error but continue processing other Shots
                print(f"Error building input for Shot {shot.id}: {e}")
                continue
        
        return inputs
    
    def _merge_prompt_with_anchors(
        self,
        render_prompt: str,
        character_refs: List[str],
        character_profile: Optional[Dict]
    ) -> Tuple[str, Dict[str, str]]:
        """
        Merge render_prompt with character visual_anchors.
        
        Implements Requirements: 5.2, 12.3
        
        Logic:
        1. Extract visual_anchor for each character in character_refs
        2. Check if render_prompt already contains visual_anchor keywords
        3. If not, intelligently insert visual_anchor into render_prompt
        4. Avoid duplication and redundancy
        
        Args:
            render_prompt: Original render prompt
            character_refs: List of character names
            character_profile: Character profile document content
            
        Returns:
            Tuple of (enhanced_prompt, character_anchors_dict)
        """
        character_anchors = {}
        
        # If no character_profile, return original prompt
        if not character_profile or not character_refs:
            return render_prompt, character_anchors
        
        # Extract characters from character_profile
        characters = character_profile.get("characters", [])
        character_map = {char["name"]: char for char in characters if "name" in char}
        
        # Collect visual_anchors for referenced characters
        anchors_to_add = []
        for char_name in character_refs:
            char_data = character_map.get(char_name)
            if char_data and "visual_anchor" in char_data:
                visual_anchor = char_data["visual_anchor"]
                character_anchors[char_name] = visual_anchor
                
                # Check if visual_anchor keywords are already in render_prompt
                # Simple check: if any significant words from visual_anchor appear in prompt
                anchor_keywords = self._extract_keywords(visual_anchor)
                prompt_lower = render_prompt.lower()
                
                # If anchor keywords are not already present, add them
                if not any(keyword in prompt_lower for keyword in anchor_keywords):
                    anchors_to_add.append(f"{char_name}: {visual_anchor}")
        
        # Merge anchors into prompt
        if anchors_to_add:
            # Insert anchors at the beginning of the prompt
            enhanced_prompt = ", ".join(anchors_to_add) + ". " + render_prompt
        else:
            enhanced_prompt = render_prompt
        
        return enhanced_prompt, character_anchors
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract significant keywords from text for comparison.
        
        Extracts words longer than 3 characters, lowercased.
        """
        words = text.lower().split()
        # Filter out short words and common words
        keywords = [
            word.strip(".,!?;:") 
            for word in words 
            if len(word.strip(".,!?;:")) > 3
        ]
        return keywords
    
    def _load_character_profile(self, episode_id: UUID) -> Optional[Dict]:
        """
        Load character_profile document for an Episode.
        
        Implements Requirement 12.2
        
        Args:
            episode_id: ID of the Episode
            
        Returns:
            Character profile content_jsonb or None if not found
        """
        documents = self.document_repo.list_for_episode(episode_id)
        
        # Find the latest character_profile document
        character_profiles = [
            doc for doc in documents 
            if doc.document_type == "character_profile"
        ]
        
        if not character_profiles:
            return None
        
        # Sort by version descending and get the latest
        character_profiles.sort(key=lambda d: d.version, reverse=True)
        latest_profile = character_profiles[0]
        
        return latest_profile.content_jsonb
    
    def _load_visual_spec(self, episode_id: UUID) -> Optional:
        """
        Load visual_spec document for an Episode.
        
        Args:
            episode_id: ID of the Episode
            
        Returns:
            DocumentModel or None if not found
        """
        documents = self.document_repo.list_for_episode(episode_id)
        
        # Find the latest visual_spec document
        visual_specs = [
            doc for doc in documents 
            if doc.document_type == "visual_spec"
        ]
        
        if not visual_specs:
            return None
        
        # Sort by version descending and get the latest
        visual_specs.sort(key=lambda d: d.version, reverse=True)
        return visual_specs[0]
    
    def _get_shot_by_id(self, shot_id: UUID) -> Optional[ShotModel]:
        """
        Get Shot by ID.
        
        Args:
            shot_id: ID of the Shot
            
        Returns:
            ShotModel or None if not found
        """
        from sqlalchemy import select
        stmt = select(ShotModel).where(ShotModel.id == shot_id)
        return self.db.scalar(stmt)
