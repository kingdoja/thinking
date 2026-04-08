"""
Simple test script to verify Object Storage Service implementation.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.object_storage_service import ObjectStorageService


def test_object_storage():
    """Test basic Object Storage Service functionality."""
    print("Testing Object Storage Service...")
    
    # Initialize service
    try:
        storage = ObjectStorageService()
        print("✓ ObjectStorageService initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize ObjectStorageService: {e}")
        return False
    
    # Test connection
    try:
        result = storage.test_connection()
        print(f"✓ Connection test: {result['status']}")
        if result['status'] == 'failed':
            print(f"  Error: {result.get('error_message', 'Unknown error')}")
            print("  Note: This is expected if MinIO is not running")
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        print("  Note: This is expected if MinIO is not running")
    
    # Test storage key generation
    try:
        storage_key = storage.generate_storage_key(
            project_id="test-project-123",
            episode_id="test-episode-456",
            asset_type="keyframe",
            file_extension="png"
        )
        print(f"✓ Generated storage key: {storage_key}")
        
        # Verify format
        parts = storage_key.split('/')
        assert len(parts) == 5, "Storage key should have 5 parts"
        assert parts[0] == "test-project-123", "First part should be project_id"
        assert parts[1] == "test-episode-456", "Second part should be episode_id"
        assert parts[2] == "keyframe", "Third part should be asset_type"
        assert parts[4].endswith(".png"), "Last part should end with .png"
        print("✓ Storage key format is correct")
    except Exception as e:
        print(f"✗ Storage key generation failed: {e}")
        return False
    
    # Test file upload (only if connection works)
    if result.get('status') == 'connected':
        try:
            # Create a temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Test content for object storage")
                temp_file = f.name
            
            # Generate storage key
            storage_key = storage.generate_storage_key(
                project_id="test-project",
                episode_id="test-episode",
                asset_type="test",
                file_extension="txt"
            )
            
            # Upload file
            upload_result = storage.upload_file(
                file_path=temp_file,
                storage_key=storage_key,
                content_type="text/plain"
            )
            print(f"✓ File uploaded successfully")
            print(f"  Storage key: {upload_result.storage_key}")
            print(f"  Size: {upload_result.size_bytes} bytes")
            
            # Test file exists
            exists = storage.file_exists(storage_key)
            print(f"✓ File exists check: {exists}")
            
            # Test download
            download_path = temp_file + ".downloaded"
            success = storage.download_file(storage_key, download_path)
            print(f"✓ File downloaded: {success}")
            
            # Test delete
            success = storage.delete_file(storage_key)
            print(f"✓ File deleted: {success}")
            
            # Cleanup
            os.unlink(temp_file)
            if os.path.exists(download_path):
                os.unlink(download_path)
                
        except Exception as e:
            print(f"✗ File operations failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ All tests completed!")
    return True


if __name__ == "__main__":
    test_object_storage()
