from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    DRAW = "draw"
    CLEAR = "clear"
    UNDO = "undo"
    REDO = "redo"


class WhiteboardAction(BaseModel):
    action_type: ActionType
    user_id: str
    username: str
    room_id: str
    timestamp: datetime = None
    data: Dict[str, Any] = {}
    
    # For drawing actions
    x: Optional[float] = None
    y: Optional[float] = None
    color: Optional[str] = None
    brush_size: Optional[int] = None
    is_drawing: Optional[bool] = None


class WhiteboardData(BaseModel):
    room_id: str
    canvas_data: Dict[str, Any] = {}
    actions: List[WhiteboardAction] = []
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WhiteboardState(BaseModel):
    room_id: str
    canvas_data: Dict[str, Any] = {}
    last_action: Optional[WhiteboardAction] = None 