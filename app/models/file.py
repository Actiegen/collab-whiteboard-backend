from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FileUpload(BaseModel):
    filename: str
    content_type: str
    size: int
    user_id: str
    room_id: str


class FileResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    user_id: str
    username: str
    room_id: str
    download_url: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class FileInfo(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    download_url: str
    created_at: datetime 