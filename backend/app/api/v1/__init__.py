"""
API v1 Router - Main entry point for all API endpoints
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api.v1.endpoints import (
    investigations,
    collection,
    entities,
    reasoning,
    auth
)

# Create main router (authentication temporarily disabled for development)
router = APIRouter()

# Register sub-routers
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
router.include_router(collection.router, prefix="/collection", tags=["collection"])
router.include_router(entities.router, prefix="/entities", tags=["entities"])
router.include_router(reasoning.router, prefix="/reasoning", tags=["reasoning"])


# Legacy status endpoint
@router.get("/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": "v1",
        "status": "operational",
        "features": {
            "investigations": "implemented",
            "entity_search": "implemented",
            "collection_agents": "implemented",
            "reasoning_engine": "implemented",
            "authentication": "implemented"
        }
    }

