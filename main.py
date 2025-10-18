import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.config.settings import get_settings
from infrastructure.database.connection import get_database_connection
from infrastructure.database.models import Base
from presentation.main_router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database connections."""
    settings = get_settings()
    db_connection = get_database_connection(settings)
    
    # Initialize database connections
    if db_connection.is_sql_database():
        try:
            engine = await db_connection.get_sql_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print(f"✅ Connected to {settings.database_type} database successfully")
        except Exception as e:
            print(f"❌ Failed to connect to {settings.database_type} database: {e}")
    
    elif db_connection.is_mongo_database():
        try:
            mongo_db = await db_connection.get_mongo_database()
            await mongo_db.command("ping")
            print(f"✅ Connected to MongoDB successfully")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
    
    yield
    
    # Cleanup connections
    await db_connection.close_connections()
    print("🔌 Database connections closed")


def create_application() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    
    # Create FastAPI application
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A FastAPI application with Clean Architecture supporting multiple databases",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    application.include_router(api_router, prefix="/api/v1")
    
    return application


# Create application instance
app = create_application()
settings = get_settings()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "status_code": 500
        }
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "database_type": settings.database_type
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )