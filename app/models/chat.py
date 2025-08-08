from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"


class MessageBase(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    room_id: str


class MessageCreate(MessageBase):
    user_id: str


class Message(MessageBase):
    id: str
    user_id: str
    username: str
    created_at: datetime
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class MessageResponse(MessageBase):
    id: str
    username: str
    created_at: datetime
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class Room(BaseModel):
    id: str
    name: str
    created_at: datetime
    created_by: str
    is_active: bool = True
    
    class Config:
        from_attributes = True


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    created_by: str 