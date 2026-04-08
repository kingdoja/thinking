"""
Asset Table Structure Validation Script

This script validates that the assets table has all required fields and constraints
for Shot-level asset management.

Requirements validated:
- 8.1: Asset has shot_id field
- 8.2: Asset has asset_type field
- 8.3: Asset has is_selected field
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text
from app.db.session import SessionLocal


def validate_asset_table_structure():
    """Validate the assets table structure."""
    print("=" * 80)
    print("Asset Table Structure Validation")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    inspector = inspect(db.bind)
    
    validation_results = {
        "required_columns": [],
        "foreign_keys": [],
        "indexes": [],
        "errors": [],
        "warnings": []
    }
    
    try:
        # Check if assets table exists
        if "assets" not in inspector.get_table_names():
            validation_results["errors"].append("Assets table does not exist")
            print_results(validation_results)
            return False
        
        print("✓ Assets table exists")
        print()
        
        # Get columns
        columns = {col["name"]: col for col in inspector.get_columns("assets")}
        
        # Requirement 8.1: Check shot_id field
        print("Checking shot_id field (Requirement 8.1)...")
        if "shot_id" in columns:
            col = columns["shot_id"]
            print(f"  ✓ shot_id field exists")
            print(f"    Type: {col['type']}")
            print(f"    Nullable: {col['nullable']}")
            validation_results["required_columns"].append("shot_id")
        else:
            validation_results["errors"].append("shot_id field is missing")
            print(f"  ✗ shot_id field is missing")
        print()
        
        # Requirement 8.2: Check asset_type field
        print("Checking asset_type field (Requirement 8.2)...")
        if "asset_type" in columns:
            col = columns["asset_type"]
            print(f"  ✓ asset_type field exists")
            print(f"    Type: {col['type']}")
            print(f"    Nullable: {col['nullable']}")
            validation_results["required_columns"].append("asset_type")
        else:
            validation_results["errors"].append("asset_type field is missing")
            print(f"  ✗ asset_type field is missing")
        print()
        
        # Requirement 8.3: Check is_selected field
        print("Checking is_selected field (Requirement 8.3)...")
        if "is_selected" in columns:
            col = columns["is_selected"]
            print(f"  ✓ is_selected field exists")
            print(f"    Type: {col['type']}")
            print(f"    Nullable: {col['nullable']}")
            print(f"    Default: {col.get('default', 'None')}")
            validation_results["required_columns"].append("is_selected")
        else:
            validation_results["errors"].append("is_selected field is missing")
            print(f"  ✗ is_selected field is missing")
        print()
        
        # Check shot_id foreign key constraint
        print("Checking shot_id foreign key constraint...")
        foreign_keys = inspector.get_foreign_keys("assets")
        shot_fk_found = False
        for fk in foreign_keys:
            if "shot_id" in fk["constrained_columns"]:
                shot_fk_found = True
                print(f"  ✓ Foreign key constraint found: {fk['name']}")
                print(f"    References: {fk['referred_table']}.{fk['referred_columns']}")
                print(f"    On Delete: {fk.get('ondelete', 'NO ACTION')}")
                validation_results["foreign_keys"].append(fk["name"])
                break
        
        if not shot_fk_found:
            validation_results["warnings"].append("shot_id foreign key constraint not found")
            print(f"  ⚠ shot_id foreign key constraint not found")
        print()
        
        # Check indexes
        print("Checking indexes...")
        indexes = inspector.get_indexes("assets")
        
        # Check for shot_id index
        shot_id_index_found = False
        for idx in indexes:
            if "shot_id" in idx["column_names"]:
                shot_id_index_found = True
                print(f"  ✓ Index on shot_id found: {idx['name']}")
                print(f"    Columns: {idx['column_names']}")
                validation_results["indexes"].append(idx["name"])
        
        if not shot_id_index_found:
            validation_results["warnings"].append("No index found on shot_id")
            print(f"  ⚠ No index found on shot_id (may impact query performance)")
        
        # List all indexes for reference
        print()
        print("All indexes on assets table:")
        for idx in indexes:
            print(f"  - {idx['name']}: {idx['column_names']}")
        print()
        
        # Check other important columns
        print("Checking other important columns...")
        important_columns = [
            "id", "project_id", "episode_id", "stage_task_id",
            "storage_key", "mime_type", "size_bytes", "version",
            "metadata_jsonb", "created_at"
        ]
        
        for col_name in important_columns:
            if col_name in columns:
                print(f"  ✓ {col_name}")
            else:
                validation_results["warnings"].append(f"{col_name} field is missing")
                print(f"  ⚠ {col_name} is missing")
        print()
        
        # Summary
        print("=" * 80)
        print("Validation Summary")
        print("=" * 80)
        print(f"Required columns found: {len(validation_results['required_columns'])}/3")
        print(f"Foreign keys found: {len(validation_results['foreign_keys'])}")
        print(f"Indexes found: {len(validation_results['indexes'])}")
        print(f"Errors: {len(validation_results['errors'])}")
        print(f"Warnings: {len(validation_results['warnings'])}")
        print()
        
        if validation_results["errors"]:
            print("ERRORS:")
            for error in validation_results["errors"]:
                print(f"  ✗ {error}")
            print()
        
        if validation_results["warnings"]:
            print("WARNINGS:")
            for warning in validation_results["warnings"]:
                print(f"  ⚠ {warning}")
            print()
        
        # Overall result
        if not validation_results["errors"]:
            print("✓ Asset table structure validation PASSED")
            return True
        else:
            print("✗ Asset table structure validation FAILED")
            return False
            
    except Exception as e:
        print(f"✗ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def print_results(results):
    """Print validation results."""
    print()
    print("=" * 80)
    print("Validation Results")
    print("=" * 80)
    for key, value in results.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    success = validate_asset_table_structure()
    sys.exit(0 if success else 1)
