from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from pydantic import BaseModel
from app.models.file import FileUpload, FileResponse
from app.services.firestore_service import FirestoreService
from app.services.storage_service import StorageService
import uuid

router = APIRouter()
firestore_service = FirestoreService()
storage_service = None  # Will be initialized when needed
security = HTTPBearer(auto_error=False)


class LegacyFileRefreshRequest(BaseModel):
    filename: str
    user_email: str
    file_type: str


async def verify_user_access_to_room(user_id: str, room_id: str) -> bool:
    """Verify if user has access to the room"""
    # TODO: Implement proper room membership verification
    # For now, we'll verify room exists and user exists
    room = await firestore_service.get_room(room_id)
    user = await firestore_service.get_user(user_id)
    return room is not None and user is not None


async def get_current_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Extract user ID from token or require user_id parameter"""
    # For now, this is a placeholder - you'll need to implement proper JWT token validation
    # or extract user info from Google OAuth token
    if credentials:
        # TODO: Validate JWT token and extract user_id
        pass
    
    # For backward compatibility, we'll still accept user_id as parameter
    return None


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    room_id: str = Form(...)
):
    """Upload a file to Google Cloud Storage"""
    global storage_service
    
    # Initialize storage service if needed
    if storage_service is None:
        try:
            storage_service = StorageService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage service not available: {str(e)}")
    
    # Validate file size
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    # Validate file type
    if file.content_type not in [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Verify user exists
    user = await firestore_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to Google Cloud Storage
        filename = await storage_service.upload_file(
            file_content, 
            file.filename, 
            file.content_type
        )
        
        # Generate secure download URL for initial response
        # Note: This URL will be used in chat but frontend should request fresh URLs for actual access
        download_url = await storage_service.generate_download_url(filename, expiration_hours=1)  # Short expiration for initial share
        
        # Save file info to database
        file_data = FileUpload(
            filename=file.filename,
            content_type=file.content_type,
            size=len(file_content),
            user_id=user_id,
            room_id=room_id
        )
        
        file_response = await firestore_service.save_file_info(
            file_data, 
            download_url, 
            user.username
        )
        
        return file_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.get("/rooms/{room_id}/files", response_model=List[FileResponse])
async def get_room_files_old(room_id: str):
    """Get all files for a room (deprecated - use version with user_id)"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    files = await firestore_service.get_room_files(room_id)
    return files


@router.get("/{file_id}/download")
async def get_file_download_url(file_id: str, user_id: str):
    """Get secure download URL for a file with access control"""
    global storage_service
    
    if storage_service is None:
        try:
            storage_service = StorageService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage service not available: {str(e)}")
    
    # Get file info from database
    file_info = await firestore_service.get_file_by_id(file_id)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify user has access to the room containing this file
    if not await verify_user_access_to_room(user_id, file_info.room_id):
        raise HTTPException(status_code=403, detail="Access denied to this file")
    
    # Generate secure download URL (24 hour expiration)
    download_url = await storage_service.generate_download_url(file_info.filename, expiration_hours=24)
    
    return {
        "download_url": download_url,
        "filename": file_info.filename,
        "content_type": file_info.content_type,
        "size": file_info.size,
        "expires_in_hours": 24
    }


@router.get("/{file_id}/preview")
async def get_file_preview_url(file_id: str, user_id: str):
    """Get secure preview URL for a file with short expiration"""
    global storage_service
    
    if storage_service is None:
        try:
            storage_service = StorageService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage service not available: {str(e)}")
    
    # Get file info from database
    file_info = await firestore_service.get_file_by_id(file_id)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify user has access to the room containing this file
    if not await verify_user_access_to_room(user_id, file_info.room_id):
        raise HTTPException(status_code=403, detail="Access denied to this file")
    
    # Generate secure preview URL (1 hour expiration)
    preview_url = await storage_service.generate_preview_url(file_info.filename, expiration_minutes=60)
    
    return {
        "preview_url": preview_url,
        "filename": file_info.filename,
        "content_type": file_info.content_type,
        "expires_in_minutes": 60
    }


@router.get("/rooms/{room_id}/files", response_model=List[FileResponse])
async def get_room_files(room_id: str, user_id: str):
    """Get all files for a room with access control"""
    # Verify user has access to the room
    if not await verify_user_access_to_room(user_id, room_id):
        raise HTTPException(status_code=403, detail="Access denied to this room")
    
    files = await firestore_service.get_room_files(room_id)
    return files


@router.delete("/{file_id}")
async def delete_file(file_id: str, user_id: str):
    """Delete a file"""
    # Get file info from database
    files = await firestore_service.get_room_files("")  # This needs to be improved
    file_info = None
    for file in files:
        if file.id == file_id:
            file_info = file
            break
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user owns the file
    if file_info.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")
    
    try:
        # Delete from Google Cloud Storage
        success = await storage_service.delete_file(file_info.filename)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file from storage")
        
        # TODO: Delete from database (implement this in FirestoreService)
        
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")


@router.post("/legacy/refresh")
async def refresh_legacy_file(request: LegacyFileRefreshRequest):
    """Generate a new signed URL for a legacy file"""
    global storage_service
    
    # Initialize storage service if needed
    if storage_service is None:
        try:
            storage_service = StorageService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage service not available: {str(e)}")
    
    try:
        # Verify the file exists in storage
        if not await storage_service.file_exists(request.filename):
            raise HTTPException(status_code=404, detail="Legacy file not found in storage")
        
        # Generate new signed URLs for the legacy file
        # Use shorter expiry for preview (1 hour) since it's for display
        preview_url = await storage_service.generate_signed_url(request.filename, expiration_hours=1)
        download_url = await storage_service.generate_signed_url(request.filename, expiration_hours=24)
        
        return {
            "preview_url": preview_url,
            "download_url": download_url,
            "filename": request.filename,
            "message": "Legacy file URLs refreshed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh legacy file URLs: {str(e)}")