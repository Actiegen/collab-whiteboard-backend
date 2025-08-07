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
        print(f"Manager.connect called: room_id={room_id}, user_id={user_id}, username={username}")
        
        await websocket.accept()
        print("WebSocket accepted")
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        
        self.active_connections[room_id].append(websocket)
        self.connection_users[websocket] = {
            "user_id": user_id,
            "username": username,
            "room_id": room_id
        }
        print(f"User added to room {room_id}")
        
        # Update user presence
        try:
            print("Updating user presence...")
            await self.firestore_service.update_user_presence(user_id, True, username)
            print("User presence updated successfully")
        except Exception as e:
            print(f"Error updating user presence: {e}")
        
        # Notify others in the room
        try:
            print("Broadcasting presence...")
            await self.broadcast_presence(room_id, user_id, username, True)
            print("Presence broadcasted successfully")
            
            # Send current user the list of all online users in the room
            room_users = self.get_room_users(room_id)
            users_message = {
                "type": "presence",
                "users": [
                    {
                        "user_id": user.user_id,
                        "username": user.username,
                        "is_online": user.is_online,
                        "timestamp": user.last_seen.isoformat()
                    }
                    for user in room_users
                ]
            }
            await websocket.send_text(json.dumps(users_message))
            print(f"Sent {len(room_users)} online users to new user")
            
        except Exception as e:
            print(f"Error broadcasting presence: {e}")

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
            await self.firestore_service.update_user_presence(user_id, False, username)
            
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
        if is_online:
            # User joined
            join_message = {
                "type": "user_joined",
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.broadcast_to_room(json.dumps(join_message), room_id)
        else:
            # User left
            leave_message = {
                "type": "user_left",
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.broadcast_to_room(json.dumps(leave_message), room_id)

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
        
        # Add file data if present
        file_url = data.get("file_url")
        file_name = data.get("file_name")
        file_type = data.get("file_type")
        
        message = await self.firestore_service.create_message(
            message_data, 
            username,
            file_url=file_url,
            file_name=file_name,
            file_type=file_type
        )
        
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
        
        action_type = data.get("action_type")
        
        # Create whiteboard action payload
        action_payload = {
            "type": "whiteboard_action",
            "action": {
                "action_type": action_type,
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat(),
                "stroke": data.get("stroke"),
                "data": data.get("data", {})
            }
        }
        
        # Save to database if it's a final action
        if action_type in ["stroke_end", "clear_canvas"]:
            action = WhiteboardAction(
                action_type=action_type,
                user_id=user_id,
                username=username,
                room_id=room_id,
                timestamp=datetime.utcnow(),
                data=data.get("stroke") or data.get("data", {}),
                x=data.get("x"),
                y=data.get("y"),
                color=data.get("color"),
                brush_size=data.get("brush_size"),
                is_drawing=data.get("is_drawing")
            )
            await self.firestore_service.save_whiteboard_action(action)
        
        # Broadcast to room (excluding sender for real-time updates)
        await self.broadcast_to_room(json.dumps(action_payload), room_id, exclude_websocket=websocket)

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