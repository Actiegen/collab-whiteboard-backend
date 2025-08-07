from google.cloud import storage
from google.cloud.storage.blob import Blob
from typing import Optional
import uuid
from datetime import datetime, timedelta
from app.config import settings


class StorageService:
    def __init__(self):
        # Use default credentials - will use gcloud auth locally and Cloud Run service account in production
        self.client = storage.Client(project=settings.google_project_id)
        self._bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            if not settings.storage_bucket_name:
                raise ValueError("STORAGE_BUCKET_NAME is not configured")
            self._bucket = self.client.bucket(settings.storage_bucket_name)
        return self._bucket

    async def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        """Upload a file to Google Cloud Storage"""
        # Generate unique filename to avoid conflicts
        file_extension = filename.split('.')[-1] if '.' in filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        
        blob = self.bucket.blob(unique_filename)
        blob.upload_from_string(
            file_content,
            content_type=content_type
        )
        
        return unique_filename

    async def generate_download_url(self, filename: str, expiration_hours: int = 24) -> str:
        """Generate a signed download URL for a file"""
        blob = self.bucket.blob(filename)
        
        # Generate signed URL
        expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
        url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET"
        )
        
        return url

    async def delete_file(self, filename: str) -> bool:
        """Delete a file from Google Cloud Storage"""
        try:
            blob = self.bucket.blob(filename)
            blob.delete()
            return True
        except Exception:
            return False

    async def get_file_info(self, filename: str) -> Optional[dict]:
        """Get file information"""
        try:
            blob = self.bucket.blob(filename)
            blob.reload()
            
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated
            }
        except Exception:
            return None

    async def file_exists(self, filename: str) -> bool:
        """Check if a file exists"""
        blob = self.bucket.blob(filename)
        return blob.exists()

    async def list_files(self, prefix: str = "") -> list:
        """List files in the bucket with optional prefix"""
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        return [blob.name for blob in blobs] 