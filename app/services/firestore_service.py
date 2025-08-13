from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from app.config import settings
from app.models.user import User, UserCreate
from app.models.chat import Message, MessageCreate, Room, RoomCreate
from app.models.whiteboard import WhiteboardData, WhiteboardAction
from app.models.file import FileUpload, FileResponse


class FirestoreService:
    def __init__(self):
        # Use default credentials - will use gcloud auth locally and Cloud Run service account in production
        self.db = firestore.Client(project=settings.google_project_id)
        self.users_collection = self.db.collection(settings.firestore_collection_users)
        self.rooms_collection = self.db.collection(settings.firestore_collection_rooms)
        self.messages_collection = self.db.collection(settings.firestore_collection_messages)
        self.whiteboard_collection = self.db.collection(settings.firestore_collection_whiteboard)
        self.files_collection = self.db.collection(settings.firestore_collection_files)

    # User Operations
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        user_doc = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "created_at": datetime.utcnow(),
            "last_seen": datetime.utcnow(),
            "is_online": False
        }
        
        self.users_collection.document(user_id).set(user_doc)
        return User(**user_doc)

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        doc = self.users_collection.document(user_id).get()
        if doc.exists:
            return User(**doc.to_dict())
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        query = self.users_collection.where(filter=FieldFilter("username", "==", username))
        docs = query.stream()
        for doc in docs:
            return User(**doc.to_dict())
        return None

    async def update_user_presence(self, user_id: str, is_online: bool, username: str = None):
        """Update user online status - creates user if doesn't exist"""
        print(f"update_user_presence called: user_id={user_id}, is_online={is_online}, username={username}")
        
        try:
            # Try to update existing user
            print("Trying to update existing user...")
            self.users_collection.document(user_id).update({
                "is_online": is_online,
                "last_seen": datetime.utcnow()
            })
            print("User updated successfully")
        except Exception as e:
            # User doesn't exist, create it
            print(f"User doesn't exist, creating new user. Error: {e}")
            if username is None:
                username = user_id.split("@")[0] if "@" in user_id else user_id
            
            user_doc = {
                "id": user_id,
                "username": username,
                "email": user_id if "@" in user_id else None,
                "is_online": is_online,
                "last_seen": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            print(f"Creating user document: {user_doc}")
            self.users_collection.document(user_id).set(user_doc)
            print("User created successfully")

    # Room Operations
    async def create_room(self, room_data: RoomCreate, created_by: str) -> Room:
        """Create a new room"""
        room_id = str(uuid.uuid4())
        room_doc = {
            "id": room_id,
            "name": room_data.name,
            "created_at": datetime.utcnow(),
            "created_by": created_by,
            "is_active": True
        }
        
        self.rooms_collection.document(room_id).set(room_doc)
        return Room(**room_doc)

    async def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID"""
        doc = self.rooms_collection.document(room_id).get()
        if doc.exists:
            return Room(**doc.to_dict())
        return None

    async def get_active_rooms(self) -> List[Room]:
        """Get all active rooms"""
        # Get all rooms since we're now actually deleting them
        docs = self.rooms_collection.stream()
        return [Room(**doc.to_dict()) for doc in docs]

    async def delete_room(self, room_id: str) -> bool:
        """Delete a room by actually removing it from Firestore"""
        try:
            room_doc = self.rooms_collection.document(room_id)
            doc = room_doc.get()
            if doc.exists:
                # Actually delete the document from Firestore
                room_doc.delete()
                return True
            return False
        except Exception as e:
            print(f"Error deleting room {room_id}: {e}")
            return False

    # Message Operations
    async def create_message(self, message_data: MessageCreate, username: str, file_url: str = None, file_name: str = None, file_type: str = None) -> Message:
        """Create a new message"""
        message_id = str(uuid.uuid4())
        message_doc = {
            "id": message_id,
            "content": message_data.content,
            "message_type": message_data.message_type,
            "room_id": message_data.room_id,
            "user_id": message_data.user_id,
            "username": username,
            "created_at": datetime.utcnow(),
            "file_url": file_url,
            "file_name": file_name,
            "file_type": file_type
        }
        
        self.messages_collection.document(message_id).set(message_doc)
        return Message(**message_doc)

    async def get_room_messages(self, room_id: str, limit: int = 50) -> List[Message]:
        """Get messages for a room"""
        query = self.messages_collection.where(
            filter=FieldFilter("room_id", "==", room_id)
        ).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        docs = query.stream()
        messages = [Message(**doc.to_dict()) for doc in docs]
        return list(reversed(messages))  # Return in chronological order

    # Whiteboard Operations
    async def save_whiteboard_action(self, action: WhiteboardAction):
        """Save a whiteboard action"""
        action_id = str(uuid.uuid4())
        action_doc = {
            "id": action_id,
            "action_type": action.action_type,
            "user_id": action.user_id,
            "username": action.username,
            "room_id": action.room_id,
            "timestamp": action.timestamp,
            "data": action.data,
            "x": action.x,
            "y": action.y,
            "color": action.color,
            "brush_size": action.brush_size,
            "is_drawing": action.is_drawing
        }
        
        self.whiteboard_collection.document(action_id).set(action_doc)

    async def get_whiteboard_state(self, room_id: str) -> Optional[WhiteboardData]:
        """Get current whiteboard state for a room"""
        try:
            query = self.whiteboard_collection.where(
                filter=FieldFilter("room_id", "==", room_id)
            ).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
            
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict()
                # Ensure required fields are present
                if "room_id" not in data:
                    data["room_id"] = room_id
                return WhiteboardData(**data)
            return None
        except Exception as e:
            print(f"Error getting whiteboard state: {e}")
            return None

    # File Operations
    async def save_file_info(self, file_data: FileUpload, download_url: str, username: str) -> FileResponse:
        """Save file information"""
        file_id = str(uuid.uuid4())
        file_doc = {
            "id": file_id,
            "filename": file_data.filename,
            "content_type": file_data.content_type,
            "size": file_data.size,
            "user_id": file_data.user_id,
            "username": username,
            "room_id": file_data.room_id,
            "download_url": download_url,
            "created_at": datetime.utcnow()
        }
        
        self.files_collection.document(file_id).set(file_doc)
        return FileResponse(**file_doc)

    async def get_room_files(self, room_id: str) -> List[FileResponse]:
        """Get files for a room"""
        query = self.files_collection.where(
            filter=FieldFilter("room_id", "==", room_id)
        ).order_by("created_at", direction=firestore.Query.DESCENDING)
        
        docs = query.stream()
        files = []
        for doc in docs:
            data = doc.to_dict()
            files.append(FileResponse(**data))
        return files

    async def get_file_by_id(self, file_id: str) -> Optional[FileResponse]:
        """Get a file by its ID"""
        try:
            doc = self.files_collection.document(file_id).get()
            if doc.exists:
                data = doc.to_dict()
                return FileResponse(**data)
            return None
        except Exception as e:
            print(f"Error getting file by ID: {e}")
            return None 