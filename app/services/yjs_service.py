import asyncio
import json
from typing import Dict, Optional, Set
from fastapi import WebSocket
from datetime import datetime


class YjsDocument:
    """Manages a single collaborative document for a room using simple message passing"""
    
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.strokes = []
        self.canvas_state = {
            "initialized": True,
            "background": "#ffffff",
            "last_updated": datetime.utcnow().isoformat()
        }
        self.connected_clients: Set[WebSocket] = set()
    
    def add_client(self, websocket: WebSocket):
        """Add a client to this document"""
        self.connected_clients.add(websocket)
    
    def remove_client(self, websocket: WebSocket):
        """Remove a client from this document"""
        self.connected_clients.discard(websocket)
    
    def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self.connected_clients)
    
    def add_stroke(self, stroke_data: dict):
        """Add a new stroke to the document"""
        stroke = {
            "id": stroke_data.get("id"),
            "points": stroke_data.get("points", []),
            "color": stroke_data.get("color", "#000000"),
            "brush_size": stroke_data.get("brush_size", 2),
            "user_id": stroke_data.get("user_id"),
            "username": stroke_data.get("username"),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.strokes.append(stroke)
    
    def clear_canvas(self, user_id: str, username: str):
        """Clear all strokes from the canvas"""
        # Clear the strokes array
        self.strokes.clear()
        
        # Update canvas state
        self.canvas_state["last_cleared_by"] = username
        self.canvas_state["last_cleared_at"] = datetime.utcnow().isoformat()
    
    def get_state(self) -> dict:
        """Get the current document state"""
        return {
            "strokes": self.strokes,
            "canvas_state": self.canvas_state
        }
    
    def to_dict(self) -> dict:
        """Export document to dictionary for persistence"""
        return {
            "room_id": self.room_id,
            "strokes": self.strokes,
            "canvas_state": self.canvas_state,
            "last_updated": datetime.utcnow().isoformat()
        }


class YjsCollaborationService:
    """Service for managing Y.js collaborative documents"""
    
    def __init__(self):
        self.documents: Dict[str, YjsDocument] = {}
        self.client_to_room: Dict[WebSocket, str] = {}
    
    def get_or_create_document(self, room_id: str) -> YjsDocument:
        """Get existing document or create new one for room"""
        if room_id not in self.documents:
            self.documents[room_id] = YjsDocument(room_id)
        return self.documents[room_id]
    
    async def connect_client(self, websocket: WebSocket, room_id: str) -> YjsDocument:
        """Connect a client to a room's document"""
        doc = self.get_or_create_document(room_id)
        doc.add_client(websocket)
        self.client_to_room[websocket] = room_id
        return doc
    
    async def disconnect_client(self, websocket: WebSocket):
        """Disconnect a client from their room"""
        room_id = self.client_to_room.get(websocket)
        if room_id and room_id in self.documents:
            doc = self.documents[room_id]
            doc.remove_client(websocket)
            
            # Clean up empty documents
            if doc.get_client_count() == 0:
                del self.documents[room_id]
        
        if websocket in self.client_to_room:
            del self.client_to_room[websocket]
    
    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle collaboration messages"""
        room_id = self.client_to_room.get(websocket)
        if not room_id or room_id not in self.documents:
            return
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "stroke_added":
                await self.handle_stroke_added(websocket, data)
            elif message_type == "canvas_cleared":
                await self.handle_canvas_cleared(websocket, data)
            elif message_type == "request_state":
                await self.send_current_state(websocket)
                
        except json.JSONDecodeError:
            print(f"Invalid JSON message: {message}")
    
    async def handle_stroke_added(self, websocket: WebSocket, data: dict):
        """Handle new stroke added"""
        room_id = self.client_to_room.get(websocket)
        if not room_id or room_id not in self.documents:
            return
        
        doc = self.documents[room_id]
        stroke_data = data.get("stroke", {})
        doc.add_stroke(stroke_data)
        
        # Broadcast to other clients
        for client in doc.connected_clients:
            if client != websocket:
                try:
                    await client.send_text(json.dumps(data))
                except:
                    await self.disconnect_client(client)
    
    async def handle_canvas_cleared(self, websocket: WebSocket, data: dict):
        """Handle canvas cleared"""
        room_id = self.client_to_room.get(websocket)
        if not room_id or room_id not in self.documents:
            return
        
        doc = self.documents[room_id]
        user_data = data.get("user", {})
        doc.clear_canvas(user_data.get("id", ""), user_data.get("name", ""))
        
        # Broadcast to other clients
        for client in doc.connected_clients:
            if client != websocket:
                try:
                    await client.send_text(json.dumps(data))
                except:
                    await self.disconnect_client(client)
    
    async def send_current_state(self, websocket: WebSocket):
        """Send current document state to a client"""
        room_id = self.client_to_room.get(websocket)
        if not room_id or room_id not in self.documents:
            return
        
        doc = self.documents[room_id]
        state_message = {
            "type": "document_state",
            "state": doc.get_state()
        }
        
        try:
            await websocket.send_text(json.dumps(state_message))
        except:
            await self.disconnect_client(websocket)
    
    async def handle_stroke_action(self, websocket: WebSocket, action_data: dict):
        """Handle drawing stroke actions"""
        room_id = self.client_to_room.get(websocket)
        if not room_id or room_id not in self.documents:
            return
        
        doc = self.documents[room_id]
        action_type = action_data.get("action_type")
        
        if action_type == "stroke_complete":
            doc.add_stroke(action_data.get("stroke", {}))
        elif action_type == "clear_canvas":
            doc.clear_canvas(
                action_data.get("user_id", ""),
                action_data.get("username", "")
            )
        
        # Broadcast action to other clients
        message = {
            "type": "whiteboard_action",
            "action": action_data
        }
        
        for client in doc.connected_clients:
            if client != websocket:
                try:
                    await client.send_text(json.dumps(message))
                except:
                    await self.disconnect_client(client)
    
    def get_document_state(self, room_id: str) -> Optional[dict]:
        """Get current state of a document"""
        if room_id in self.documents:
            return self.documents[room_id].to_dict()
        return None
    
    async def restore_document_state(self, room_id: str, state_data: dict):
        """Restore document from saved state"""
        doc = self.get_or_create_document(room_id)
        
        # Restore strokes
        if "strokes" in state_data:
            for stroke in state_data["strokes"]:
                doc.strokes.append(stroke)
        
        # Restore canvas state
        if "canvas_state" in state_data:
            for key, value in state_data["canvas_state"].items():
                doc.canvas_state.set(key, value)


# Global service instance
yjs_service = YjsCollaborationService()
