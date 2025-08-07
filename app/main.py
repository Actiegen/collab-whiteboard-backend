from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from app.config import settings
from app.api import api_router
from app.services.websocket_service import manager
from datetime import datetime

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real-time collaborative whiteboard and chat API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Collab Whiteboard API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/test")
async def test_endpoint():
    """Test endpoint that doesn't require Google Cloud"""
    return {
        "message": "Backend is working!",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "FastAPI server running",
            "WebSocket support ready",
            "API documentation available",
            "CORS configured"
        ]
    }


# WebSocket endpoint for real-time communication
@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    """WebSocket endpoint for real-time chat and whiteboard collaboration"""
    try:
        # Get user info
        from app.services.firestore_service import FirestoreService
        firestore_service = FirestoreService()
        user = await firestore_service.get_user(user_id)
        
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return
        
        # Connect to room
        await manager.connect(websocket, room_id, user_id, user.username)
        
        # Send initial room state
        initial_state = {
            "type": "room_joined",
            "room_id": room_id,
            "user_id": user_id,
            "username": user.username,
            "message": f"{user.username} joined the room"
        }
        await websocket.send_text(json.dumps(initial_state))
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                message_type = message_data.get("type")
                
                if message_type == "chat_message":
                    await manager.handle_chat_message(websocket, message_data)
                
                elif message_type == "whiteboard_action":
                    await manager.handle_whiteboard_action(websocket, message_data)
                
                elif message_type == "file_upload":
                    await manager.handle_file_upload(websocket, message_data)
                
                elif message_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
                else:
                    # Echo back unknown message types
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 