# Object Storage Service Setup

## Overview

The Object Storage Service provides a unified interface for managing media files in S3-compatible storage (S3, MinIO, etc.).

## Configuration

Add the following environment variables to your `.env` file:

```env
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=thinking-media
S3_REGION=us-east-1
S3_USE_SSL=false
```

## Storage Key Format

Files are organized using the following key structure:

```
{project_id}/{episode_id}/{asset_type}/{YYYYMMDD}/{uuid}.{extension}
```

Example:
```
abc123/def456/keyframe/20260407/550e8400-e29b-41d4-a716-446655440000.png
```

This format ensures:
- Uniqueness through UUID
- Organization by project, episode, and asset type
- Time-based organization with date prefix
- Proper file extension handling

## Usage

### Initialize the Service

```python
from app.services.object_storage_service import ObjectStorageService

storage = ObjectStorageService()
```

### Test Connection

```python
result = storage.test_connection()
print(result)
# {'status': 'connected', 'bucket': 'thinking-media', ...}
```

### Generate Storage Key

```python
storage_key = storage.generate_storage_key(
    project_id="project-123",
    episode_id="episode-456",
    asset_type="keyframe",
    file_extension="png"
)
```

### Upload File

```python
result = storage.upload_file(
    file_path="/path/to/local/file.png",
    storage_key=storage_key,
    content_type="image/png",
    metadata={"shot_id": "shot-789"}
)
print(f"Uploaded to: {result.url}")
```

### Download File

```python
success = storage.download_file(
    storage_key=storage_key,
    local_path="/path/to/save/file.png"
)
```

### Get Presigned URL

```python
url = storage.get_url(
    storage_key=storage_key,
    expires_in=3600  # 1 hour
)
```

### Delete File

```python
success = storage.delete_file(storage_key=storage_key)
```

### Check File Existence

```python
exists = storage.file_exists(storage_key)
```

### Get File Metadata

```python
metadata = storage.get_file_metadata(storage_key)
print(metadata)
# {
#     'size_bytes': 12345,
#     'content_type': 'image/png',
#     'last_modified': datetime(...),
#     'metadata': {'shot_id': 'shot-789'}
# }
```

## Testing

Run the test script to verify the setup:

```bash
cd apps/api
python scripts/test_object_storage.py
```

## MinIO Setup (Local Development)

For local development, you can use MinIO as an S3-compatible storage:

1. Start MinIO using Docker:
```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minio \
  -e MINIO_ROOT_PASSWORD=minio123 \
  minio/minio server /data --console-address ":9001"
```

2. Access MinIO Console at http://localhost:9001
3. The bucket `thinking-media` will be created automatically

## Error Handling

The service handles common errors:

- **FileNotFoundError**: Raised when trying to upload a non-existent local file
- **RuntimeError**: Raised for S3 operation failures (upload, download, delete)
- **ClientError**: Boto3 client errors are caught and converted to RuntimeError

## Requirements

- boto3>=1.34.0

## Implementation Details

- Uses boto3 S3 client with path-style addressing
- Automatically creates bucket if it doesn't exist
- Generates presigned URLs for secure file access
- Supports custom metadata for files
- Thread-safe for concurrent operations
