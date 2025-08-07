from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.user import User, UserCreate, UserResponse
from app.services.firestore_service import FirestoreService

router = APIRouter()
firestore_service = FirestoreService()


@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """Create a new user"""
    # Check if username already exists
    existing_user = await firestore_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user = await firestore_service.create_user(user_data)
    return UserResponse(**user.dict())


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    user = await firestore_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user.dict())


@router.get("/username/{username}", response_model=UserResponse)
async def get_user_by_username(username: str):
    """Get user by username"""
    user = await firestore_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user.dict())


@router.put("/{user_id}/presence")
async def update_user_presence(user_id: str, is_online: bool):
    """Update user online status"""
    await firestore_service.update_user_presence(user_id, is_online)
    return {"message": "User presence updated successfully"} 