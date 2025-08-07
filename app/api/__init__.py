from fastapi import APIRouter
from .chat import router as chat_router
from .whiteboard import router as whiteboard_router
from .files import router as files_router
from .users import router as users_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(whiteboard_router, prefix="/whiteboard", tags=["whiteboard"])
api_router.include_router(files_router, prefix="/files", tags=["files"]) 