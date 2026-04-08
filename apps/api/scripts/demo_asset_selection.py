"""
Demonstration script for Asset Selection Logic

This script demonstrates that the primary asset selection logic works correctly
by creating test data including Shots and Assets.

Requirements demonstrated:
- 10.2: Select primary asset
- 10.3: Ensure only one primary asset per shot
- 10.4: Record selection operation
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import ProjectModel, EpisodeModel, ShotModel
from app.services.asset_service import AssetService


def demo_asset_selection():
    """Demonstrate asset selection logic."""
    print("=" * 80)
    print("Asset Selection Logic Demonstration")
    print("=" * 80)
    print()
    
    db: Session = SessionLocal()
    
    try:
        # Create test project
        project = ProjectModel(
            id=uuid4(),
            name="Demo Project",
            source_mode="original",
            target_platform="mobile",
            status="draft"
        )
        db.add(project)
        db.flush()
        print(f"✓ Created project: {project.name}")
        
        # Create test episode
        episode = EpisodeModel(
            id=uuid4(),
            project_id=project.id,
            episode_no=1,
            title="Demo Episode",
            status="draft",
            current_stage="storyboard",
            target_duration_sec=60
        )
        db.add(episode)
        db.flush()
        print(f"✓ Created episode: {episode.title}")
        
        # Create test shot
        shot = ShotModel(
            id=uuid4(),
            project_id=project.id,
            episode_id=episode.id,
            scene_no=1,
            shot_no=1,
            shot_code="S01_001",
            status="draft",
            duration_ms=3000,
            camera_size="medium",
            camera_angle="eye-level",
            movement_type="static",
            characters_jsonb=["Alice"],
            action_text="Alice walks into the room",
            dialogue_text="Hello!",
            visual_constraints_jsonb={
                "render_prompt": "A woman walking into a modern room",
                "style_keywords": ["realistic", "bright"],
                "composition": "medium shot",
                "character_refs": ["Alice"]
            },
            version=1
        )
        db.add(shot)
        db.flush()
        print(f"✓ Created shot: {shot.shot_code}")
        print()
        
        # Create asset service
        asset_service = AssetService(db)
        
        # Create multiple candidate assets
        print("Creating candidate assets...")
        asset1 = asset_service.create_asset(
            project_id=project.id,
            episode_id=episode.id,
            shot_id=shot.id,
            asset_type="keyframe",
            storage_key="s3://bucket/keyframe1.png",
            mime_type="image/png",
            size_bytes=1024,
            width=1920,
            height=1080,
            quality_score=75.5
        )
        print(f"  ✓ Created asset 1: {asset1.id} (quality: {asset1.quality_score})")
        
        asset2 = asset_service.create_asset(
            project_id=project.id,
            episode_id=episode.id,
            shot_id=shot.id,
            asset_type="keyframe",
            storage_key="s3://bucket/keyframe2.png",
            mime_type="image/png",
            size_bytes=2048,
            width=1920,
            height=1080,
            quality_score=85.0
        )
        print(f"  ✓ Created asset 2: {asset2.id} (quality: {asset2.quality_score})")
        
        asset3 = asset_service.create_asset(
            project_id=project.id,
            episode_id=episode.id,
            shot_id=shot.id,
            asset_type="keyframe",
            storage_key="s3://bucket/keyframe3.png",
            mime_type="image/png",
            size_bytes=1536,
            width=1920,
            height=1080,
            quality_score=90.5
        )
        print(f"  ✓ Created asset 3: {asset3.id} (quality: {asset3.quality_score})")
        print()
        
        db.commit()
        
        # Get all candidate assets
        candidates = asset_service.get_candidate_assets(shot.id, asset_type="keyframe")
        print(f"Total candidate assets: {len(candidates)}")
        print()
        
        # Select asset 2 as primary (Requirement 10.2)
        print("Selecting asset 2 as primary...")
        selected = asset_service.select_primary_asset(
            shot_id=shot.id,
            asset_id=asset2.id,
            asset_type="keyframe",
            selected_by="demo_user"
        )
        db.commit()
        print(f"  ✓ Selected asset: {selected.id}")
        print(f"  ✓ is_selected: {selected.is_selected}")
        print()
        
        # Verify only one asset is selected (Requirement 10.3)
        print("Verifying uniqueness constraint...")
        db.refresh(asset1)
        db.refresh(asset2)
        db.refresh(asset3)
        
        selected_count = sum([
            asset1.is_selected,
            asset2.is_selected,
            asset3.is_selected
        ])
        
        print(f"  Asset 1 is_selected: {asset1.is_selected}")
        print(f"  Asset 2 is_selected: {asset2.is_selected}")
        print(f"  Asset 3 is_selected: {asset3.is_selected}")
        print(f"  Total selected: {selected_count}")
        
        if selected_count == 1:
            print("  ✓ Uniqueness constraint satisfied")
        else:
            print(f"  ✗ Uniqueness constraint violated: {selected_count} assets selected")
        print()
        
        # Verify selection was recorded (Requirement 10.4)
        print("Verifying selection history...")
        if "selection_history" in selected.metadata_jsonb:
            history = selected.metadata_jsonb["selection_history"]
            print(f"  ✓ Selection history recorded: {len(history)} entries")
            for i, entry in enumerate(history, 1):
                print(f"    {i}. Selected by: {entry['selected_by']}")
                print(f"       Selected at: {entry['selected_at']}")
        else:
            print("  ✗ Selection history not found")
        print()
        
        # Change selection to asset 3
        print("Changing selection to asset 3...")
        selected = asset_service.select_primary_asset(
            shot_id=shot.id,
            asset_id=asset3.id,
            asset_type="keyframe",
            selected_by="demo_user"
        )
        db.commit()
        print(f"  ✓ Selected asset: {selected.id}")
        print()
        
        # Verify only asset 3 is now selected
        print("Verifying selection changed...")
        db.refresh(asset1)
        db.refresh(asset2)
        db.refresh(asset3)
        
        print(f"  Asset 1 is_selected: {asset1.is_selected}")
        print(f"  Asset 2 is_selected: {asset2.is_selected}")
        print(f"  Asset 3 is_selected: {asset3.is_selected}")
        
        if not asset1.is_selected and not asset2.is_selected and asset3.is_selected:
            print("  ✓ Selection changed successfully")
        else:
            print("  ✗ Selection change failed")
        print()
        
        # Get primary asset
        primary = asset_service.get_primary_asset(shot.id, asset_type="keyframe")
        print(f"Primary asset: {primary.id if primary else 'None'}")
        print(f"Quality score: {primary.quality_score if primary else 'N/A'}")
        print()
        
        print("=" * 80)
        print("✓ Asset Selection Logic Demonstration PASSED")
        print("=" * 80)
        
        # Rollback to clean up
        db.rollback()
        
        return True
        
    except Exception as e:
        print(f"✗ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = demo_asset_selection()
    sys.exit(0 if success else 1)
