"""
Updated FastAPI REST API with MSSQL Integration
Implements the specific workflow: retrieve ideal answer -> extract concepts -> retrieve student answer -> grade and save
"""
import logging
import time
import urllib.parse
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from ..models.database import DatabaseManager, Question, StudentAnswer
from ..services.database_service import DatabaseService
from ..services.llm_service import llm_service, LLMError
from ..utils.config import settings, validate_api_keys


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
    logger.info("Starting AI Examiner API with MSSQL integration...")
    
    try:
        # Validate API keys
        api_validation = validate_api_keys()
        if not api_validation["selected_provider_valid"]:
            logger.error(f"Invalid API configuration for provider: {settings.llm_provider}")
            raise RuntimeError("LLM API keys not properly configured")
        
        # Initialize database
        connection_string = build_connection_string()
        logger.info(f"Connecting to database: {settings.db_server}:{settings.db_port}/{settings.db_name}")
        
        db_manager = DatabaseManager(connection_string)
        database_service = DatabaseService(db_manager)
        
        # Test LLM connection
        if not llm_service.validate_connection():
            logger.error("Failed to validate LLM connection")
            raise RuntimeError("Cannot connect to LLM provider")
        
        logger.info("AI Examiner API started successfully with MSSQL integration")
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
    title="AI Examiner API - MSSQL Edition",
    description="AI-powered narrative answer grading system with MSSQL database integration",
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


# Request/Response Models
class GradingWorkflowRequest(BaseModel):
    """Request for complete grading workflow"""
    question_id: str
    student_id: str


class GradingWorkflowResponse(BaseModel):
    """Response from grading workflow"""
    Score: str
    Justification: str
    Key_Concepts_Covered: List[str]
    Percentage: str
    Passed: bool
    ProcessingTimeMs: float
    ConfidenceScore: float
    GradingResultId: str


class CreateQuestionRequest(BaseModel):
    """Request to create a new question"""
    question_id: str
    subject: str
    topic: str
    question_text: str
    ideal_answer: str
    max_marks: float
    passing_threshold: float = 60.0
    difficulty_level: str = "intermediate"


class CreateStudentAnswerRequest(BaseModel):
    """Request to create a student answer"""
    student_id: str
    question_id: str
    answer_text: str
    language: str = "en"


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    logger.error(f"Value error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid request", "detail": str(exc)}
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request, exc: LLMError):
    logger.error(f"LLM error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "LLM service unavailable", "detail": str(exc)}
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "database": "connected" if db_manager else "disconnected"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database and LLM connectivity"""
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
        "status": "healthy" if (llm_connected and db_connected) else "degraded",
        "timestamp": time.time(),
        "llm_provider": provider_info,
        "api_keys_valid": api_validation,
        "llm_connected": llm_connected,
        "database_connected": db_connected,
        "database_url": f"{settings.db_server}:{settings.db_port}/{settings.db_name}"
    }


# Core Workflow Endpoints

@app.post("/grade/workflow", response_model=GradingWorkflowResponse)
async def complete_grading_workflow(request: GradingWorkflowRequest) -> GradingWorkflowResponse:
    """
    Complete AI grading workflow as specified:
    1. Retrieve ideal answer and marks from database
    2. Extract and save semantic understanding (key concepts) in database  
    3. Retrieve student's submitted answer from database
    4. Grade and save results in required format
    
    Returns exactly: {"Score": "X/10", "Justification": "...", "Key_Concepts_Covered": ["Concept A (2/3 points) - Reason..."]}
    """
    start_time = time.time()
    
    try:
        if not database_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        logger.info(f"Starting grading workflow for student {request.student_id}, question {request.question_id}")
        
        # Execute the complete workflow
        result = await database_service.complete_grading_workflow(
            question_id=request.question_id,
            student_id=request.student_id
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Grading workflow completed for student {request.student_id}: "
            f"{result['Score']} in {processing_time:.2f}ms"
        )
        
        return GradingWorkflowResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"Grading workflow failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grading workflow failed: {str(e)}"
        )


@app.post("/grade/batch/workflow")
async def batch_grading_workflow(request: List[GradingWorkflowRequest]) -> Dict[str, Any]:
    """
    Process multiple grading workflows in batch
    """
    start_time = time.time()
    results = []
    successful = 0
    failed = 0
    
    logger.info(f"Starting batch grading workflow for {len(request)} requests")
    
    for grading_request in request:
        request_start = time.time()
        try:
            result = await database_service.complete_grading_workflow(
                question_id=grading_request.question_id,
                student_id=grading_request.student_id
            )
            
            request_time = (time.time() - request_start) * 1000
            
            results.append({
                "student_id": grading_request.student_id,
                "question_id": grading_request.question_id,
                "result": result,
                "processing_time_ms": request_time,
                "success": True,
                "error_message": None
            })
            successful += 1
            
        except Exception as e:
            request_time = (time.time() - request_start) * 1000
            logger.error(f"Failed batch request for {grading_request.student_id}: {e}")
            
            results.append({
                "student_id": grading_request.student_id,
                "question_id": grading_request.question_id,
                "result": None,
                "processing_time_ms": request_time,
                "success": False,
                "error_message": str(e)
            })
            failed += 1
    
    total_time = (time.time() - start_time) * 1000
    
    logger.info(f"Batch grading completed: {successful} successful, {failed} failed in {total_time:.2f}ms")
    
    return {
        "results": results,
        "total_processed": len(request),
        "total_successful": successful,
        "total_failed": failed,
        "total_processing_time_ms": total_time
    }


# Individual Step Endpoints

@app.get("/questions/{question_id}")
async def get_question(question_id: str) -> Dict[str, Any]:
    """Step 1: Retrieve ideal answer and marks for a question"""
    try:
        question = database_service.get_question_with_ideal_answer(question_id)
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        return {
            "id": question.id,
            "question_id": question.question_id,
            "subject": question.subject,
            "topic": question.topic,
            "question_text": question.question_text,
            "ideal_answer": question.ideal_answer,
            "max_marks": question.max_marks,
            "passing_threshold": question.passing_threshold,
            "difficulty_level": question.difficulty_level,
            "key_concepts_count": len(question.key_concepts)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/questions/{question_id}/extract-concepts")
async def extract_and_save_concepts(question_id: str) -> Dict[str, Any]:
    """Step 2: Extract key concepts from ideal answer and save to database"""
    try:
        question = database_service.get_question_with_ideal_answer(question_id)
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        start_time = time.time()
        key_concepts = await database_service.extract_and_save_key_concepts(question)
        processing_time = (time.time() - start_time) * 1000
        
        concepts_data = []
        for concept in key_concepts:
            concepts_data.append({
                "id": concept.id,
                "concept_name": concept.concept_name,
                "concept_description": concept.concept_description,
                "importance_score": concept.importance_score,
                "keywords": concept.keywords,
                "max_points": concept.max_points,
                "extraction_method": concept.extraction_method
            })
        
        return {
            "question_id": question_id,
            "key_concepts": concepts_data,
            "concepts_count": len(concepts_data),
            "processing_time_ms": processing_time,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error extracting concepts for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/students/{student_id}/answers/{question_id}")
async def get_student_answer(student_id: str, question_id: str) -> Dict[str, Any]:
    """Step 3: Retrieve student's submitted answer"""
    try:
        student_answer = database_service.get_student_answer(student_id, question_id)
        if not student_answer:
            raise HTTPException(
                status_code=404, 
                detail=f"Student answer not found for student {student_id}, question {question_id}"
            )
        
        return {
            "id": student_answer.id,
            "answer_id": student_answer.answer_id,
            "student_id": student_answer.student_id,
            "question_id": question_id,
            "answer_text": student_answer.answer_text,
            "submitted_at": student_answer.submitted_at.isoformat(),
            "word_count": student_answer.word_count,
            "language": student_answer.language
        }
        
    except Exception as e:
        logger.error(f"Error retrieving student answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Management Endpoints

@app.post("/questions")
async def create_question(request: CreateQuestionRequest) -> Dict[str, Any]:
    """Create a new question with ideal answer"""
    try:
        question = database_service.create_question(
            question_id=request.question_id,
            subject=request.subject,
            topic=request.topic,
            question_text=request.question_text,
            ideal_answer=request.ideal_answer,
            max_marks=request.max_marks,
            passing_threshold=request.passing_threshold,
            difficulty_level=request.difficulty_level
        )
        
        return {
            "id": question.id,
            "question_id": question.question_id,
            "subject": question.subject,
            "topic": question.topic,
            "max_marks": question.max_marks,
            "created_at": question.created_at.isoformat(),
            "message": f"Question {request.question_id} created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating question: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/student-answers")
async def create_student_answer(request: CreateStudentAnswerRequest) -> Dict[str, Any]:
    """Create a new student answer"""
    try:
        student_answer = database_service.create_student_answer(
            student_id=request.student_id,
            question_id=request.question_id,
            answer_text=request.answer_text,
            language=request.language
        )
        
        return {
            "id": student_answer.id,
            "answer_id": student_answer.answer_id,
            "student_id": student_answer.student_id,
            "question_id": request.question_id,
            "word_count": student_answer.word_count,
            "submitted_at": student_answer.submitted_at.isoformat(),
            "message": f"Student answer created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating student answer: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/students/{student_id}/results")
async def get_student_results(student_id: str) -> Dict[str, Any]:
    """Get all grading results for a student"""
    try:
        results = database_service.get_grading_results_by_student(student_id)
        return {
            "student_id": student_id,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error retrieving results for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Database Information Endpoints

@app.get("/database/info")
async def get_database_info() -> Dict[str, Any]:
    """Get database connection information"""
    return {
        "server": settings.db_server,
        "port": settings.db_port,
        "database": settings.db_name,
        "driver": settings.db_driver,
        "connected": db_manager is not None
    }


@app.get("/database/tables")
async def get_database_tables() -> Dict[str, Any]:
    """Get information about database tables"""
    try:
        if not db_manager:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        session = db_manager.get_session()
        
        # Get table counts
        question_count = session.query(Question).count()
        student_answer_count = session.query(StudentAnswer).count()
        
        session.close()
        
        return {
            "tables": {
                "questions": question_count,
                "student_answers": student_answer_count,
                "key_concepts": "Available",
                "grading_results": "Available",
                "concept_evaluations": "Available",
                "audit_logs": "Available"
            },
            "status": "connected"
        }
        
    except Exception as e:
        logger.error(f"Error getting database table info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Provider Information
@app.get("/provider/info")
async def get_provider_info() -> Dict[str, Any]:
    """Get information about the current LLM provider and configuration"""
    return llm_service.get_provider_info()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.mssql_api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )