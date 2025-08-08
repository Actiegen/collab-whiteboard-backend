from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.chat import Message, MessageCreate, Room, RoomCreate, MessageResponse
from app.services.firestore_service import FirestoreService

router = APIRouter()
firestore_service = FirestoreService()


@router.post("/rooms/", response_model=Room)
async def create_room(room_data: RoomCreate):
    """Create a new chat room"""
    room = await firestore_service.create_room(room_data, room_data.created_by)
    return room


@router.get("/rooms/", response_model=List[Room])
async def get_active_rooms():
    """Get all active rooms"""
    rooms = await firestore_service.get_active_rooms()
    return rooms


@router.get("/rooms/{room_id}", response_model=Room)
async def get_room(room_id: str):
    """Get room by ID"""
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.get("/rooms/{room_id}/messages", response_model=List[MessageResponse])
async def get_room_messages(room_id: str, limit: int = Query(50, ge=1, le=100)):
    """Get messages for a room"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    messages = await firestore_service.get_room_messages(room_id, limit)
    return [MessageResponse(**message.dict()) for message in messages]


@router.post("/rooms/{room_id}/messages", response_model=MessageResponse)
async def create_message(room_id: str, message_data: MessageCreate):
    """Create a new message in a room"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Get username for the user
    user = await firestore_service.get_user(message_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    message = await firestore_service.create_message(message_data, user.username)
    return MessageResponse(**message.dict())


@router.delete("/rooms/{room_id}")
async def delete_room(room_id: str):
    """Delete a room by setting is_active to False"""
    # Verify room exists
    room = await firestore_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    success = await firestore_service.delete_room(room_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete room")
    
    return {"message": "Room deleted successfully"} 