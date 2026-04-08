"""
Shot Validation Service

Validates Shot data completeness and consistency.

Implements Requirements: 1.1, 2.1, 3.5, 4.2
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import ShotModel, DocumentModel
from app.repositories.shot_repository import ShotRepository
from app.repositories.document_repository import DocumentRepository


@dataclass
class ValidationError:
    """Validation error"""
    field_path: str
    error_type: str  # missing_required, invalid_format, invalid_reference, inconsistency
    message: str
    shot_id: Optional[str] = None
    episode_id: Optional[str] = None


@dataclass
class ValidationWarning:
    """Validation warning"""
    field_path: str
    warning_type: str  # missing_optional, suboptimal, inconsistency
    message: str
    suggestion: str
    shot_id: Optional[str] = None
    episode_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class ShotValidationService:
    """
    Service for validating Shot data completeness and consistency.
    
    Responsibilities:
    1. Validate Shot record completeness (Requirement 1.1)
    2. Validate visual_constraints schema (Requirement 2.1)
    3. Validate Shot-visual_spec consistency (Requirement 3.5, 4.2)
    4. Validate character_refs references (Requirement 2.5)
    """
    
    # Required fields for Shot model
    REQUIRED_FIELDS = [
        'id', 'project_id', 'episode_id', 'scene_no', 'shot_no',
        'shot_code', 'status', 'duration_ms', 'characters_jsonb',
        'visual_constraints_jsonb', 'version', 'created_at', 'updated_at'
    ]
    
    # Required fields in visual_constraints
    VISUAL_CONSTRAINTS_REQUIRED = [
        'render_prompt', 'style_keywords', 'composition', 'character_refs'
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.shot_repo = ShotRepository(db)
        self.doc_repo = DocumentRepository(db)
    
    def validate_shot_completeness(self, shot: ShotModel) -> ValidationResult:
        """
        Validate Shot record completeness.
        
        Implements Requirement 1.1: Check all required fields exist
        
        Args:
            shot: Shot model to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        shot_id = str(shot.id)
        episode_id = str(shot.episode_id)
        
        # Check required fields are not None
        if shot.scene_no is None:
            errors.append(ValidationError(
                field_path='scene_no',
                error_type='missing_required',
                message='scene_no field is None',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if shot.shot_no is None:
            errors.append(ValidationError(
                field_path='shot_no',
                error_type='missing_required',
                message='shot_no field is None',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if not shot.shot_code:
            errors.append(ValidationError(
                field_path='shot_code',
                error_type='missing_required',
                message='shot_code field is empty',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if shot.duration_ms is None or shot.duration_ms <= 0:
            errors.append(ValidationError(
                field_path='duration_ms',
                error_type='invalid_format',
                message=f'duration_ms is invalid: {shot.duration_ms}',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        # Check optional fields (warnings only)
        if not shot.camera_size:
            warnings.append(ValidationWarning(
                field_path='camera_size',
                warning_type='missing_optional',
                message='camera_size field is empty',
                suggestion='Recommend filling camera_size for complete shot information',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if not shot.camera_angle:
            warnings.append(ValidationWarning(
                field_path='camera_angle',
                warning_type='missing_optional',
                message='camera_angle field is empty',
                suggestion='Recommend filling camera_angle for complete shot information',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats={'shot_id': shot_id, 'episode_id': episode_id}
        )
    
    def validate_visual_constraints_schema(
        self,
        visual_constraints: dict,
        shot_id: Optional[str] = None,
        episode_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate visual_constraints schema.
        
        Implements Requirement 2.1: Validate visual_constraints structure
        
        Args:
            visual_constraints: visual_constraints dict to validate
            shot_id: Optional shot ID for error reporting
            episode_id: Optional episode ID for error reporting
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Check if visual_constraints is a valid dict
        if not visual_constraints or not isinstance(visual_constraints, dict):
            errors.append(ValidationError(
                field_path='visual_constraints_jsonb',
                error_type='invalid_format',
                message='visual_constraints_jsonb is not a valid dict',
                shot_id=shot_id,
                episode_id=episode_id
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings
            )
        
        # Check required fields
        for field in self.VISUAL_CONSTRAINTS_REQUIRED:
            if field not in visual_constraints:
                errors.append(ValidationError(
                    field_path=f'visual_constraints_jsonb.{field}',
                    error_type='missing_required',
                    message=f'visual_constraints missing required field: {field}',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        # Validate render_prompt
        if 'render_prompt' in visual_constraints:
            prompt = visual_constraints['render_prompt']
            if not prompt or not isinstance(prompt, str):
                errors.append(ValidationError(
                    field_path='visual_constraints_jsonb.render_prompt',
                    error_type='invalid_format',
                    message='render_prompt is empty or not a string',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
            elif len(prompt) < 10:
                warnings.append(ValidationWarning(
                    field_path='visual_constraints_jsonb.render_prompt',
                    warning_type='suboptimal',
                    message=f'render_prompt is too short ({len(prompt)} characters)',
                    suggestion='Recommend render_prompt to be at least 10 characters',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        # Validate style_keywords
        if 'style_keywords' in visual_constraints:
            if not isinstance(visual_constraints['style_keywords'], list):
                errors.append(ValidationError(
                    field_path='visual_constraints_jsonb.style_keywords',
                    error_type='invalid_format',
                    message='style_keywords is not an array',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        # Validate character_refs
        if 'character_refs' in visual_constraints:
            if not isinstance(visual_constraints['character_refs'], list):
                errors.append(ValidationError(
                    field_path='visual_constraints_jsonb.character_refs',
                    error_type='invalid_format',
                    message='character_refs is not an array',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_shot_visual_spec_consistency(
        self,
        episode_id: UUID,
        version: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate Shot records consistency with visual_spec document.
        
        Implements Requirement 3.5, 4.2: Validate Shot-visual_spec consistency
        
        Args:
            episode_id: Episode ID to validate
            version: Optional version to validate (defaults to latest)
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        stats = {}
        
        # Get shots for episode
        if version is None:
            shots = self.shot_repo.list_current_for_episode(episode_id)
            if shots:
                version = shots[0].version
        else:
            stmt = (
                select(ShotModel)
                .where(
                    ShotModel.episode_id == episode_id,
                    ShotModel.version == version
                )
                .order_by(ShotModel.scene_no.asc(), ShotModel.shot_no.asc())
            )
            shots = list(self.db.scalars(stmt).all())
        
        stats['shot_count'] = len(shots)
        stats['version'] = version
        
        if not shots:
            warnings.append(ValidationWarning(
                field_path='shots',
                warning_type='inconsistency',
                message=f'No shots found for episode {episode_id}',
                suggestion='Ensure Storyboard Agent has created shots',
                episode_id=str(episode_id)
            ))
            return ValidationResult(
                is_valid=True,
                errors=errors,
                warnings=warnings,
                stats=stats
            )
        
        # Get visual_spec document
        visual_spec = self._get_document_by_version(
            episode_id, 'visual_spec', version
        )
        
        if not visual_spec:
            warnings.append(ValidationWarning(
                field_path='visual_spec',
                warning_type='inconsistency',
                message=f'No visual_spec document found for episode {episode_id} version {version}',
                suggestion='Ensure Storyboard Agent creates visual_spec and Shot records together',
                episode_id=str(episode_id)
            ))
            return ValidationResult(
                is_valid=True,
                errors=errors,
                warnings=warnings,
                stats=stats
            )
        
        content = visual_spec.content_jsonb
        
        # Validate shot_count
        if 'shot_count' in content:
            expected_count = content['shot_count']
            actual_count = len(shots)
            stats['expected_shot_count'] = expected_count
            
            if expected_count != actual_count:
                errors.append(ValidationError(
                    field_path='shot_count',
                    error_type='inconsistency',
                    message=f'Shot count mismatch: visual_spec.shot_count={expected_count}, actual Shot count={actual_count}',
                    episode_id=str(episode_id)
                ))
        
        # Validate shots array
        if 'shots' in content and isinstance(content['shots'], list):
            spec_shots = content['shots']
            stats['spec_shots_count'] = len(spec_shots)
            
            # Create shot_code to Shot mapping
            shot_map = {shot.shot_code: shot for shot in shots}
            
            # Check each spec shot has corresponding Shot record
            for idx, spec_shot in enumerate(spec_shots):
                if 'shot_id' not in spec_shot:
                    warnings.append(ValidationWarning(
                        field_path=f'visual_spec.shots[{idx}]',
                        warning_type='inconsistency',
                        message=f'visual_spec shot at index {idx} missing shot_id',
                        suggestion='Ensure all shots in visual_spec have shot_id',
                        episode_id=str(episode_id)
                    ))
                    continue
                
                shot_code = spec_shot.get('shot_id')
                if shot_code not in shot_map:
                    warnings.append(ValidationWarning(
                        field_path='visual_spec.shots',
                        warning_type='inconsistency',
                        message=f'visual_spec shot_id "{shot_code}" not found in Shot table',
                        suggestion='Check Storyboard Agent committer logic',
                        episode_id=str(episode_id)
                    ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats
        )
    
    def validate_character_refs(
        self,
        episode_id: UUID,
        shots: Optional[List[ShotModel]] = None
    ) -> ValidationResult:
        """
        Validate character_refs references are valid.
        
        Implements Requirement 2.5: Validate character references
        
        Args:
            episode_id: Episode ID to validate
            shots: Optional list of shots (if None, fetches current shots)
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Get shots if not provided
        if shots is None:
            shots = self.shot_repo.list_current_for_episode(episode_id)
        
        if not shots:
            return ValidationResult(
                is_valid=True,
                errors=errors,
                warnings=warnings
            )
        
        # Get character_profile document
        character_profile = self._get_latest_document(episode_id, 'character_profile')
        
        if not character_profile:
            warnings.append(ValidationWarning(
                field_path='character_profile',
                warning_type='missing_optional',
                message=f'Episode {episode_id} has no character_profile document',
                suggestion='Create character_profile document to validate character references',
                episode_id=str(episode_id)
            ))
            return ValidationResult(
                is_valid=True,
                errors=errors,
                warnings=warnings
            )
        
        # Extract character names
        character_names = self._extract_character_names(character_profile)
        
        # Validate each Shot's character_refs
        for shot in shots:
            vc = shot.visual_constraints_jsonb
            if not vc or 'character_refs' not in vc:
                continue
            
            char_refs = vc['character_refs']
            if not isinstance(char_refs, list):
                continue
            
            for char_name in char_refs:
                if char_name not in character_names:
                    errors.append(ValidationError(
                        field_path='visual_constraints_jsonb.character_refs',
                        error_type='invalid_reference',
                        message=f'Character "{char_name}" does not exist in character_profile',
                        shot_id=str(shot.id),
                        episode_id=str(episode_id)
                    ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _get_latest_document(
        self,
        episode_id: UUID,
        document_type: str
    ) -> Optional[DocumentModel]:
        """Get latest version of document."""
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.episode_id == episode_id,
                DocumentModel.document_type == document_type
            )
            .order_by(DocumentModel.version.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
    
    def _get_document_by_version(
        self,
        episode_id: UUID,
        document_type: str,
        version: int
    ) -> Optional[DocumentModel]:
        """Get document by specific version."""
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.episode_id == episode_id,
                DocumentModel.document_type == document_type,
                DocumentModel.version == version
            )
            .limit(1)
        )
        return self.db.scalar(stmt)
    
    def _extract_character_names(self, character_profile: DocumentModel) -> set:
        """Extract character names from character_profile."""
        content = character_profile.content_jsonb
        character_names = set()
        
        if 'characters' in content and isinstance(content['characters'], list):
            for char in content['characters']:
                if 'name' in char:
                    character_names.add(char['name'])
        
        return character_names
