from google.cloud import storage
from google.oauth2 import service_account
from google.auth import impersonated_credentials
import google.auth
from typing import Optional
import uuid
from datetime import datetime, timedelta
from app.config import settings


class StorageService:
    def __init__(self):
        # Use Application Default Credentials (ADC)
        # Locally: uses gcloud auth application-default login
        # Production: uses Cloud Run default service account
        self.credentials, self.project = google.auth.default()
        self.client = storage.Client(project=settings.google_project_id, credentials=self.credentials)
        self._bucket = None
        
        # For signed URLs, we need to impersonate a service account
        # In production (Cloud Run), this will be the same service account
        # Locally, we impersonate the App Engine default service account
        self.signing_credentials = self._get_signing_credentials()

    def _get_signing_credentials(self):
        """Get credentials capable of signing URLs"""
        # App Engine default service account email
        service_account_email = f"{settings.google_project_id}@appspot.gserviceaccount.com"
        
        try:
            # Try to create impersonated credentials for signing
            signing_credentials = impersonated_credentials.Credentials(
                source_credentials=self.credentials,
                target_principal=service_account_email,
                target_scopes=['https://www.googleapis.com/auth/devstorage.read_write'],
            )
            return signing_credentials
        except Exception as e:
            print(f"Warning: Could not create signing credentials: {e}")
            return None

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
        """Generate a signed URL for secure file access"""
        blob = self.bucket.blob(filename)
        
        # Generate signed URL that expires after specified hours
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET",
            credentials=self.signing_credentials
        )
        
        return url

    async def generate_preview_url(self, filename: str, expiration_minutes: int = 60) -> str:
        """Generate a short-lived signed URL for file preview"""
        blob = self.bucket.blob(filename)
        
        # Generate short-lived signed URL for previews
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
            credentials=self.signing_credentials
        )
        
        return url

    async def generate_signed_url(self, filename: str, expiration_hours: int = 1) -> str:
        """Generate a signed URL for any file access with custom expiration"""
        blob = self.bucket.blob(filename)
        
        # Generate signed URL that expires after specified hours
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET",
            credentials=self.signing_credentials
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