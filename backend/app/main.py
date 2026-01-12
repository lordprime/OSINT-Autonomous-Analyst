from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any
import logging

from app.core.config import settings
from app.core.database import neo4j_driver, timescale_pool, elasticsearch_client
from app.api.v1 import router as api_v1_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#  ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="OSINT Autonomous Analyst API",
    description="Government-grade OSINT analysis platform with autonomous reasoning",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ============================================
# CORS Configuration
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Request Timing Middleware
# ============================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ============================================
# Global Exception Handler
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.DEBUG else None
            },
            "timestamp": int(time.time())
        }
    )

# ============================================
# Startup & Shutdown Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("Starting OSINT Autonomous Analyst API...")
    
    # Verify database connections
    try:
        # Test Neo4j
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
        logger.info("✓ Neo4j connection successful")
        
        # Test TimescaleDB
        with timescale_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        logger.info("✓ TimescaleDB connection successful")
        
        # Test Elasticsearch
        if elasticsearch_client.ping():
            logger.info("✓ Elasticsearch connection successful")
        
        logger.info("All database connections verified")
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    logger.info("Shutting down OSINT Autonomous Analyst API...")
    
    # Close Neo4j
    neo4j_driver.close()
    logger.info("✓ Neo4j connection closed")
    
    # Close TimescaleDB pool
    timescale_pool.close()
    logger.info("✓ TimescaleDB connection closed")
    
    # Close Elasticsearch
    elasticsearch_client.close()
    logger.info("✓ Elasticsearch connection closed")

# ============================================
# API Routes
# ============================================

# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")

# ============================================
# Health Check Endpoints
# ============================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "version": "0.1.0"
    }

@app.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with database status"""
    health_status = {
        "status": "healthy",
        "timestamp": int(time.time()),
        "services": {}
    }
    
    # Check Neo4j
    try:
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        health_status["services"]["neo4j"] = "healthy"
    except Exception as e:
        health_status["services"]["neo4j"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check TimescaleDB
    try:
        with timescale_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        health_status["services"]["timescaledb"] = "healthy"
    except Exception as e:
        health_status["services"]["timescaledb"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Elasticsearch
    try:
        if elasticsearch_client.ping():
            health_status["services"]["elasticsearch"] = "healthy"
        else:
            health_status["services"]["elasticsearch"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["elasticsearch"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OSINT Autonomous Analyst API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/health"
    }

# ============================================
# Run Application
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
