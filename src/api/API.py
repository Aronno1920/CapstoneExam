"""
FastAPI REST API for AI Examiner System - Unified with APIRouters
"""
import time
import logging
from fastapi import FastAPI
from typing import Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from ..utils.config import settings

# Import routers
from .routers import question_api, grade_api, llm_api
# Import database services
from ..utils.database_manager import DatabaseManager
from ..services.question_service import QuestionService


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database services on application startup"""
    try:
        # Build database connection string
        if settings.use_windows_auth:
            db_url = f"mssql+pyodbc://@{settings.db_server},{settings.db_port}/{settings.db_name}?driver={settings.db_driver}&trusted_connection=yes"
        else:
            db_url = f"mssql+pyodbc://{settings.db_username}:{settings.db_password}@{settings.db_server},{settings.db_port}/{settings.db_name}?driver={settings.db_driver}"
        
        # Initialize database manager
        db_manager = DatabaseManager(db_url)
        question_service = QuestionService(db_manager)
        
        # Set services in routers
        question_api.set_database_services(db_manager, question_service)
        grade_api.set_database_services(db_manager, question_service)
        
        logger.info("Database services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database services: {e}")
        # Don't raise here to allow API to start without database
        logger.warning("API starting without database connection")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Application shutdown")


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


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "name": "AI Examiner",
        "version": "2.0.0",
        "description": "AI-powered narrative answer grading system",
        "routers": {
            "question": "/question - MSSQL question operations and workflow (hidden from docs)",
            "grade": "/grade - Grading workflow operations",
            "llm": "/llm - LLM operations and in-memory grading (hidden from docs)"
        },
        "docs": "/docs",
        "health": "/health",
        "timestamp": time.time()
    }


# Custom OpenAPI schema to hide Schemas section
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        del openapi_schema["components"]["schemas"]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Include routers (use prefixes defined in each router and show in Swagger)
app.include_router(question_api.router)
app.include_router(grade_api.router)
app.include_router(llm_api.router)
