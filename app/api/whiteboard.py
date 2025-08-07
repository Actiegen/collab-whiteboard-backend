from fastapi import APIRouter, HTTPException
from typing import List
from app.models.whiteboard import WhiteboardData, WhiteboardAction
from app.services.firestore_service import FirestoreService

router = APIRouter()
firestore_service = FirestoreService()


@router.get("/rooms/{room_id}/state", response_model=WhiteboardData)
async def get_whiteboard_state(room_id: str):
    """Get current whiteboard state for a room"""
    # Verify room exists
    from app.services.firestore_service import FirestoreService
    room_service = FirestoreService()
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    state = await firestore_service.get_whiteboard_state(room_id)
    if not state:
        # Return empty state if no data exists
        return WhiteboardData(
            room_id=room_id,
            canvas_data={},
            actions=[],
            last_updated=None
        )
    return state


@router.post("/rooms/{room_id}/actions")
async def save_whiteboard_action(room_id: str, action: WhiteboardAction):
    """Save a whiteboard action"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Verify user exists
    user = await firestore_service.get_user(action.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Set room_id from path parameter
    action.room_id = room_id
    
    await firestore_service.save_whiteboard_action(action)
    return {"message": "Action saved successfully"}


@router.delete("/rooms/{room_id}/clear")
async def clear_whiteboard(room_id: str, user_id: str):
    """Clear the whiteboard for a room"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Verify user exists
    user = await firestore_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create clear action
    clear_action = WhiteboardAction(
        action_type="clear",
        user_id=user_id,
        username=user.username,
        room_id=room_id,
        timestamp=None,
        data={}
    )
    
    await firestore_service.save_whiteboard_action(clear_action)
    return {"message": "Whiteboard cleared successfully"} 