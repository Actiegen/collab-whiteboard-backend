from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
from datetime import datetime
from app.models.chat import Message, MessageCreate
from app.models.whiteboard import WhiteboardAction
from app.models.user import UserPresence
from app.services.firestore_service import FirestoreService


class ConnectionManager:
    def __init__(self):
        # Store active connections by room_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store user info for each connection
        self.connection_users: Dict[WebSocket, dict] = {}
        self.firestore_service = FirestoreService()

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, username: str):
        """Connect a user to a room"""
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        
        self.active_connections[room_id].append(websocket)
        self.connection_users[websocket] = {
            "user_id": user_id,
            "username": username,
            "room_id": room_id
        }
        
        # Update user presence
        await self.firestore_service.update_user_presence(user_id, True)
        
        # Notify others in the room
        await self.broadcast_presence(room_id, user_id, username, True)

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a user"""
        user_info = self.connection_users.get(websocket)
        if user_info:
            room_id = user_info["room_id"]
            user_id = user_info["user_id"]
            username = user_info["username"]
            
            # Remove from active connections
            if room_id in self.active_connections:
                self.active_connections[room_id].remove(websocket)
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
            
            # Remove user info
            del self.connection_users[websocket]
            
            # Update user presence
            await self.firestore_service.update_user_presence(user_id, False)
            
            # Notify others in the room
            await self.broadcast_presence(room_id, user_id, username, False)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific user"""
        await websocket.send_text(message)

    async def broadcast_to_room(self, message: str, room_id: str, exclude_websocket: WebSocket = None):
        """Broadcast a message to all users in a room"""
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != exclude_websocket:
                    try:
                        await connection.send_text(message)
                    except:
                        # Remove broken connections
                        await self.disconnect(connection)

    async def broadcast_presence(self, room_id: str, user_id: str, username: str, is_online: bool):
        """Broadcast user presence to room"""
        presence_message = {
            "type": "presence",
            "user_id": user_id,
            "username": username,
            "is_online": is_online,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_room(json.dumps(presence_message), room_id)

    async def handle_chat_message(self, websocket: WebSocket, data: dict):
        """Handle incoming chat message"""
        user_info = self.connection_users.get(websocket)
        if not user_info:
            return
        
        room_id = user_info["room_id"]
        user_id = user_info["user_id"]
        username = user_info["username"]
        
        # Create message in database
        message_data = MessageCreate(
            content=data["content"],
            message_type=data.get("message_type", "text"),
            room_id=room_id,
            user_id=user_id
        )
        
        message = await self.firestore_service.create_message(message_data, username)
        
        # Broadcast to room
        message_payload = {
            "type": "chat_message",
            "message": {
                "id": message.id,
                "content": message.content,
                "message_type": message.message_type,
                "user_id": message.user_id,
                "username": message.username,
                "created_at": message.created_at.isoformat(),
                "file_url": message.file_url,
                "file_name": message.file_name,
                "file_type": message.file_type
            }
        }
        
        await self.broadcast_to_room(json.dumps(message_payload), room_id)

    async def handle_whiteboard_action(self, websocket: WebSocket, data: dict):
        """Handle incoming whiteboard action"""
        user_info = self.connection_users.get(websocket)
        if not user_info:
            return
        
        room_id = user_info["room_id"]
        user_id = user_info["user_id"]
        username = user_info["username"]
        
        # Create whiteboard action
        action = WhiteboardAction(
            action_type=data["action_type"],
            user_id=user_id,
            username=username,
            room_id=room_id,
            timestamp=datetime.utcnow(),
            data=data.get("data", {}),
            x=data.get("x"),
            y=data.get("y"),
            color=data.get("color"),
            brush_size=data.get("brush_size"),
            is_drawing=data.get("is_drawing")
        )
        
        # Save to database
        await self.firestore_service.save_whiteboard_action(action)
        
        # Broadcast to room
        action_payload = {
            "type": "whiteboard_action",
            "action": {
                "action_type": action.action_type,
                "user_id": action.user_id,
                "username": action.username,
                "timestamp": action.timestamp.isoformat(),
                "data": action.data,
                "x": action.x,
                "y": action.y,
                "color": action.color,
                "brush_size": action.brush_size,
                "is_drawing": action.is_drawing
            }
        }
        
        await self.broadcast_to_room(json.dumps(action_payload), room_id)

    async def handle_file_upload(self, websocket: WebSocket, data: dict):
        """Handle file upload notification"""
        user_info = self.connection_users.get(websocket)
        if not user_info:
            return
        
        room_id = user_info["room_id"]
        user_id = user_info["user_id"]
        username = user_info["username"]
        
        # Create file message
        message_data = MessageCreate(
            content=f"Uploaded: {data['filename']}",
            message_type="file",
            room_id=room_id,
            user_id=user_id
        )
        
        message = await self.firestore_service.create_message(message_data, username)
        
        # Broadcast file upload to room
        file_payload = {
            "type": "file_upload",
            "file": {
                "id": data["file_id"],
                "filename": data["filename"],
                "content_type": data["content_type"],
                "size": data["size"],
                "download_url": data["download_url"],
                "user_id": user_id,
                "username": username,
                "created_at": datetime.utcnow().isoformat()
            }
        }
        
        await self.broadcast_to_room(json.dumps(file_payload), room_id)

    def get_room_users(self, room_id: str) -> List[UserPresence]:
        """Get list of users in a room"""
        users = []
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                user_info = self.connection_users.get(connection)
                if user_info:
                    users.append(UserPresence(
                        user_id=user_info["user_id"],
                        username=user_info["username"],
                        is_online=True,
                        last_seen=datetime.utcnow()
                    ))
        return users


# Global connection manager instance
manager = ConnectionManager() 