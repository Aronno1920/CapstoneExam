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
from sqlalchemy import text

from ..models.database import DatabaseManager
from ..models.schemas import (
    GradingRequest, GradingResponse, BatchGradingRequest, BatchGradingResponse,
    IdealAnswer, StudentAnswer, KeyConcept
)
from ..services.database_service import DatabaseService
from ..services.llm_service import llm_service, LLMError
from ..utils.config import settings, validate_api_keys

# Import routers
from .routers import database, grade, llm


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
    
    # Use the exact working connection string from our test
    server = settings.db_server
    if server in ["Ahmed-PC", "localhost", "."]:
        server = "localhost"
    
    # Check if we should use Windows Authentication
    if getattr(settings, 'use_windows_auth', True):  # Default to Windows Auth
        # Use the exact format that worked in our test
        connection_string = (
            f"mssql+pyodbc://@{server}:{settings.db_port}/{settings.db_name}"
            f"?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes&timeout=30"
        )
    else:
        # SQL Server Authentication
        password = urllib.parse.quote_plus(settings.db_password)
        connection_string = (
            f"mssql+pyodbc://{settings.db_username}:{password}@"
            f"{server}:{settings.db_port}/{settings.db_name}"
            f"?driver=ODBC+Driver+17+for+SQL+Server&timeout=30"
        )
    
    logger.info(f"Attempting database connection to: {server}:{settings.db_port}/{settings.db_name}")
    logger.info(f"Connection string: {connection_string}")
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
                
                # Use the exact working connection string from our successful test
                working_connection_string = (
                    f"mssql+pyodbc://@localhost:1433/{settings.db_name}"
                    f"?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes&timeout=30"
                )
                
                logger.info("Attempting database connection with tested working format...")
                db_manager = DatabaseManager(working_connection_string)
                
                # Test the connection
                session = db_manager.get_session()
                result = session.execute(text("SELECT COUNT(*) FROM questions")).fetchone()
                question_count = result[0]
                session.close()
                
                logger.info(f"✅ Database connected successfully! Found {question_count} questions.")
                
                # Initialize database service
                database_service = DatabaseService(db_manager)
                
                # Set database services in database router
                database.set_database_services(db_manager, database_service)
                logger.info("MSSQL database services initialized")
                    
            else:
                logger.info("Database router will operate in unavailable mode")
        except Exception as db_error:
            logger.warning(f"Database connection failed: {db_error}")
            logger.info("Database router will operate in unavailable mode")
            logger.info("API will start without database functionality")
        
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
    title="AI Examiner",
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

# Include routers (use prefixes defined in each router and show in Swagger)
app.include_router(database.router)
app.include_router(grade.router)
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
            "database": "/database - MSSQL database operations and workflow (hidden from docs)",
            "llm": "/llm - LLM operations and in-memory grading (hidden from docs)"
        },
        "internal_docs": "/internal/routes",
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


@app.get("/internal/routes", include_in_schema=False)
async def get_internal_routes() -> Dict[str, Any]:
    """Get information about internal/hidden routes (not shown in main Swagger docs)"""
    return {
        "message": "Internal API Routes - Not shown in main documentation",
        "database_routes": {
            "prefix": "/database",
            "description": "MSSQL database operations and workflow",
            "endpoints": [
                "GET /database/info - Database connection info",
                "GET /database/tables - Database table information",
                "GET /database/questions/{question_id} - Get question details",
                "POST /database/questions - Create new question",
                "GET /database/students/{student_id}/answers/{question_id} - Get student answer",
                "POST /database/student-answers - Create student answer",
                "POST /database/grade/workflow - Complete grading workflow"
            ]
        },
        "llm_routes": {
            "prefix": "/llm",
            "description": "LLM operations and in-memory grading",
            "endpoints": [
                "POST /llm/grade - Grade single answer",
                "POST /llm/grade/batch - Batch grade answers",
                "POST /llm/analyze/concepts - Extract key concepts",
                "POST /llm/analyze/similarity - Analyze semantic similarity",
                "GET /llm/provider/info - LLM provider information",
                "POST /llm/provider/test - Test LLM connection"
            ]
        },
        "access_note": "These routes are functional but hidden from the main Swagger documentation for cleaner API presentation",
        "main_docs": "/docs",
        "timestamp": time.time()
    }


