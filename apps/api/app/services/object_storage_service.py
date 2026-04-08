"""
Object Storage Service for managing media files in S3/MinIO.

This service provides a unified interface for uploading, downloading, and managing
media assets in object storage.
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse

from app.core.config import settings

try:
    from botocore.exceptions import ClientError
except ImportError:  # boto3/botocore not installed (e.g. in unit-test environments)
    ClientError = Exception  # type: ignore[assignment,misc]


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    storage_key: str
    url: str
    size_bytes: int
    checksum: Optional[str] = None


@dataclass
class StorageKeyComponents:
    """Components of a storage key for organizing files."""
    project_id: str
    episode_id: str
    asset_type: str
    filename: str


class ObjectStorageService:
    """
    Service for managing files in object storage (S3/MinIO).
    
    Responsibilities:
    1. Upload files to object storage
    2. Generate unique storage_key for each file
    3. Return accessible URLs
    4. Download files from storage
    5. Delete files from storage
    """
    
    def __init__(self):
        """Initialize the S3 client with configuration from settings."""
        import boto3
        from botocore.client import Config

        # Parse endpoint to extract host and port
        endpoint_url = settings.s3_endpoint
        
        # Configure S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            ),
            use_ssl=settings.s3_use_ssl
        )
        
        self.bucket = settings.s3_bucket
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the configured bucket exists, create if it doesn't."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket)
                except ClientError as create_error:
                    raise RuntimeError(
                        f"Failed to create bucket {self.bucket}: {create_error}"
                    )
            else:
                raise RuntimeError(
                    f"Failed to access bucket {self.bucket}: {e}"
                )
    
    def generate_storage_key(
        self,
        project_id: str,
        episode_id: str,
        asset_type: str,
        file_extension: str
    ) -> str:
        """
        Generate a unique storage key for a file.
        
        Format: {project_id}/{episode_id}/{asset_type}/{uuid}.{extension}
        
        Args:
            project_id: Project UUID
            episode_id: Episode UUID
            asset_type: Type of asset (keyframe, audio, subtitle, preview, etc.)
            file_extension: File extension (without dot)
            
        Returns:
            str: Unique storage key
        """
        unique_id = uuid.uuid4()
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        
        # Format: project_id/episode_id/asset_type/YYYYMMDD/uuid.ext
        storage_key = f"{project_id}/{episode_id}/{asset_type}/{timestamp}/{unique_id}.{file_extension}"
        
        return storage_key
    
    def upload_file(
        self,
        file_path: str,
        storage_key: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """
        Upload a file to object storage.
        
        Args:
            file_path: Local file path to upload
            storage_key: Storage key (path) in the bucket
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the file
            
        Returns:
            UploadResult: Upload result with storage_key and URL
            
        Raises:
            FileNotFoundError: If the local file doesn't exist
            RuntimeError: If upload fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Prepare extra args
        extra_args = {
            'ContentType': content_type
        }
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.bucket,
                storage_key,
                ExtraArgs=extra_args
            )
            
            # Generate URL
            url = self.get_url(storage_key)
            
            return UploadResult(
                storage_key=storage_key,
                url=url,
                size_bytes=file_size
            )
            
        except ClientError as e:
            raise RuntimeError(f"Failed to upload file: {e}")
    
    def download_file(
        self,
        storage_key: str,
        local_path: str
    ) -> bool:
        """
        Download a file from object storage.
        
        Args:
            storage_key: Storage key of the file to download
            local_path: Local path where to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket,
                storage_key,
                local_path
            )
            
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            raise RuntimeError(f"Failed to download file: {e}")
    
    def delete_file(
        self,
        storage_key: str
    ) -> bool:
        """
        Delete a file from object storage.
        
        Args:
            storage_key: Storage key of the file to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=storage_key
            )
            return True
            
        except ClientError as e:
            raise RuntimeError(f"Failed to delete file: {e}")
    
    def get_url(
        self,
        storage_key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Get a presigned URL for accessing a file.
        
        Args:
            storage_key: Storage key of the file
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Presigned URL for accessing the file
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': storage_key
                },
                ExpiresIn=expires_in
            )
            return url
            
        except ClientError as e:
            raise RuntimeError(f"Failed to generate URL: {e}")
    
    def file_exists(
        self,
        storage_key: str
    ) -> bool:
        """
        Check if a file exists in object storage.
        
        Args:
            storage_key: Storage key to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket,
                Key=storage_key
            )
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            raise RuntimeError(f"Failed to check file existence: {e}")
    
    def get_file_metadata(
        self,
        storage_key: str
    ) -> Optional[Dict[str, any]]:
        """
        Get metadata for a file in object storage.
        
        Args:
            storage_key: Storage key of the file
            
        Returns:
            Dict with file metadata or None if file doesn't exist
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket,
                Key=storage_key
            )
            
            return {
                'size_bytes': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return None
            raise RuntimeError(f"Failed to get file metadata: {e}")
    
    def test_connection(self) -> Dict[str, any]:
        """
        Test the connection to object storage.
        
        Returns:
            Dict with connection status and details
            
        Raises:
            RuntimeError: If connection test fails
        """
        try:
            # Try to list buckets to verify credentials
            response = self.s3_client.list_buckets()
            
            # Check if our bucket exists
            bucket_exists = any(
                bucket['Name'] == self.bucket 
                for bucket in response.get('Buckets', [])
            )
            
            # Try to access the bucket
            self.s3_client.head_bucket(Bucket=self.bucket)
            
            return {
                'status': 'connected',
                'bucket': self.bucket,
                'bucket_exists': bucket_exists,
                'endpoint': settings.s3_endpoint,
                'region': settings.s3_region
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = str(e)
            
            return {
                'status': 'failed',
                'error_code': error_code,
                'error_message': error_message,
                'bucket': self.bucket,
                'endpoint': settings.s3_endpoint
            }
