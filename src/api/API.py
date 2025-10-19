"""
FastAPI REST API for AI Examiner System - Unified with APIRouters
"""
import logging
import time
from typing import Dict, Any
from contextlib import asynccontextmanager
import urllib.parse

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..models.database import DatabaseManager
from ..models.schemas import (
    GradingRequest, GradingResponse, BatchGradingRequest, BatchGradingResponse,
    IdealAnswer, StudentAnswer, KeyConcept
)
from ..services.database_service import DatabaseService
from ..services.llm_service import llm_service, LLMError
from ..utils.config import settings, validate_api_keys

# Import routers
from .routers import database, llm


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global database components
db_manager: DatabaseManager = None
database_service: DatabaseService = None


def build_connection_string() -> str:
    """Build MSSQL connection string from settings"""
    if settings.database_url and not settings.database_url.startswith("sqlite"):
        return settings.database_url
    
    # Build from individual components
    password = urllib.parse.quote_plus(settings.db_password)
    driver = urllib.parse.quote_plus(settings.db_driver)
    
    connection_string = (
        f"mssql+pyodbc://{settings.db_username}:{password}@"
        f"{settings.db_server}:{settings.db_port}/{settings.db_name}"
        f"?driver={driver}"
    )
    return connection_string


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    global db_manager, database_service
    
    # Startup
    logger.info("Starting AI Examiner API with Router-based structure...")
    
    try:
        # Validate API keys
        api_validation = validate_api_keys()
        if not api_validation["selected_provider_valid"]:
            logger.error(f"Invalid API configuration for provider: {settings.llm_provider}")
            raise RuntimeError("LLM API keys not properly configured")
        
        # Initialize database (if MSSQL configured)
        try:
            connection_string = build_connection_string()
            if not connection_string.startswith("sqlite"):
                logger.info(f"Connecting to database: {settings.db_server}:{settings.db_port}/{settings.db_name}")
                db_manager = DatabaseManager(connection_string)
                database_service = DatabaseService(db_manager)
                
                # Set database services in database router
                database.set_database_services(db_manager, database_service)
                
                logger.info("MSSQL database connected successfully")
            else:
                logger.info("Database router will operate in unavailable mode")
        except Exception as db_error:
            logger.warning(f"Database connection failed: {db_error}")
            logger.info("Database router will operate in unavailable mode")
        
        # Test LLM connection
        if not llm_service.validate_connection():
            logger.error("Failed to validate LLM connection")
            raise RuntimeError("Cannot connect to LLM provider")
        
        logger.info("AI Examiner API started successfully with routers")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down AI Examiner API...")
    if db_manager:
        db_manager.close()


# Create FastAPI app
app = FastAPI(
    title="AI Examiner API",
    description="AI-powered narrative answer grading system with organized routers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(database.router)
app.include_router(llm.router)



# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "name": "AI Examiner API",
        "version": "2.0.0",
        "description": "AI-powered narrative answer grading system",
        "routers": {
            "database": "/database - MSSQL database operations and workflow",
            "llm": "/llm - LLM operations and in-memory grading"
        },
        "docs": "/docs",
        "health": "/health",
        "timestamp": time.time()
    }


# Health check endpoints
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "database": "connected" if db_manager else "not_configured",
        "llm": "connected" if llm_service.validate_connection() else "disconnected",
        "routers": ["database", "llm"]
    }


@app.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check including LLM and database connectivity"""
    llm_connected = llm_service.validate_connection()
    provider_info = llm_service.get_provider_info()
    api_validation = validate_api_keys()
    
    # Test database connection
    db_connected = False
    if db_manager:
        try:
            session = db_manager.get_session()
            session.execute("SELECT 1")
            session.close()
            db_connected = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
    
    return {
        "status": "healthy" if llm_connected else "degraded",
        "timestamp": time.time(),
        "llm_provider": provider_info,
        "api_keys_valid": api_validation,
        "llm_connected": llm_connected,
        "database_connected": db_connected,
        "database_url": f"{settings.db_server}:{settings.db_port}/{settings.db_name}" if db_manager else "not_configured",
        "routers": {
            "database": "/database - Available" if db_connected else "/database - Unavailable",
            "llm": "/llm - Available" if llm_connected else "/llm - Error"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.api.API:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
