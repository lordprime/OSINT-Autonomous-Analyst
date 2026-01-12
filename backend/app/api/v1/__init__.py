"""
API v1 Router - Main entry point for all API endpoints
"""

from fastapi import APIRouter

# Import sub-routers (will be implemented by other agents)
# from app.api.v1.endpoints import investigations, entities, collection, reasoning, audit

router = APIRouter()

# Placeholder routes - will be expanded by Agent 3, 4, 5

@router.get("/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": "v1",
        "status": "operational",
        "features": {
            "investigations": "planned",
            "entity_search": "planned",
            "collection_agents": "planned",
            "reasoning_engine": "planned",
            "audit_logs": "ready"
        }
    }

# Routes will be added by other agents:
# router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
# router.include_router(entities.router, prefix="/entities", tags=["entities"])
# router.include_router(collection.router, prefix="/collection", tags=["collection"])
# router.include_router(reasoning.router, prefix="/reasoning", tags=["reasoning"])
# router.include_router(audit.router, prefix="/audit", tags=["audit"])
