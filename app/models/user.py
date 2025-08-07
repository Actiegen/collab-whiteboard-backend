from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class User(UserBase):
    id: str
    created_at: datetime
    last_seen: Optional[datetime] = None
    is_online: bool = False
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_online: bool = False
    
    class Config:
        from_attributes = True


class UserPresence(BaseModel):
    user_id: str
    username: str
    is_online: bool
    last_seen: Optional[datetime] = None 