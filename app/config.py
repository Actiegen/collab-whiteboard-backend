from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # FastAPI Settings
    app_name: str = "Collab Whiteboard API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Settings
    allowed_origins: list = ["http://localhost:3000", "https://your-frontend-domain.vercel.app"]
    
    # Google Cloud Settings
    google_project_id: str = os.getenv("GOOGLE_PROJECT_ID", "")
    # google_application_credentials is optional - when not set, uses ADC
    google_application_credentials: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Firestore Settings
    firestore_collection_users: str = "users"
    firestore_collection_rooms: str = "rooms"
    firestore_collection_messages: str = "messages"
    firestore_collection_whiteboard: str = "whiteboard_data"
    firestore_collection_files: str = "files"
    
    # Cloud Storage Settings
    storage_bucket_name: str = os.getenv("STORAGE_BUCKET_NAME", "")
    storage_bucket_url: str = os.getenv("STORAGE_BUCKET_URL", "")
    
    # File Upload Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    # WebSocket Settings
    websocket_ping_interval: int = 25
    websocket_ping_timeout: int = 10
    
    class Config:
        env_file = ".env"


settings = Settings() 