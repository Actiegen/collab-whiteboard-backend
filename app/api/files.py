from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
from app.models.file import FileUpload, FileResponse
from app.services.firestore_service import FirestoreService
from app.services.storage_service import StorageService
import uuid

router = APIRouter()
firestore_service = FirestoreService()
storage_service = None  # Will be initialized when needed


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
        
        # Generate download URL
        download_url = await storage_service.generate_download_url(filename)
        
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
async def get_room_files(room_id: str):
    """Get all files for a room"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    files = await firestore_service.get_room_files(room_id)
    return files


@router.get("/{file_id}/download")
async def get_file_download_url(file_id: str):
    """Get download URL for a file"""
    # Get file info from database
    files = await firestore_service.get_room_files("")  # This needs to be improved
    file_info = None
    for file in files:
        if file.id == file_id:
            file_info = file
            break
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Generate new download URL
    download_url = await storage_service.generate_download_url(file_info.filename)
    
    return {
        "download_url": download_url,
        "filename": file_info.filename,
        "content_type": file_info.content_type,
        "size": file_info.size
    }


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