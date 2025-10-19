"""
Database Operations Router
Handles all MSSQL database-related endpoints and workflow
"""
import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...models.database import DatabaseManager, Question, StudentAnswer as DBStudentAnswer
from ...services.database_service import DatabaseService
from ...utils.config import settings

logger = logging.getLogger(__name__)

# Router for database operations
router = APIRouter(
    prefix="/database",
    tags=["Database Operations"],
    responses={404: {"description": "Not found"}},
)

# Global database components (will be set from main app)
db_manager: DatabaseManager = None
database_service: DatabaseService = None


def set_database_services(db_mgr: DatabaseManager, db_svc: DatabaseService):
    """Set database services from main application"""
    global db_manager, database_service
    db_manager = db_mgr
    database_service = db_svc


# Request/Response Models
class GradingWorkflowRequest(BaseModel):
    """Request for complete MSSQL grading workflow"""
    question_id: str
    student_id: str


class GradingWorkflowResponse(BaseModel):
    """Response from MSSQL grading workflow"""
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


def check_database_service():
    """Helper to check if database service is available"""
    if not database_service:
        raise HTTPException(
            status_code=503, 
            detail="Database service not available. Please configure MSSQL connection."
        )


# Core MSSQL Workflow Endpoints

@router.post("/grade/workflow", response_model=GradingWorkflowResponse)
async def complete_grading_workflow(request: GradingWorkflowRequest) -> GradingWorkflowResponse:
    """
    Complete AI grading workflow with MSSQL database:
    1. Retrieve ideal answer and marks from database
    2. Extract and save semantic understanding (key concepts) in database  
    3. Retrieve student's submitted answer from database
    4. Grade and save results in required format
    
    Returns exactly: {"Score": "X/10", "Justification": "...", "Key_Concepts_Covered": ["Concept A (2/3 points) - Reason..."]}
    """
    check_database_service()
    start_time = time.time()
    
    try:
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


@router.post("/grade/batch/workflow")
async def batch_grading_workflow(requests: List[GradingWorkflowRequest]) -> Dict[str, Any]:
    """
    Process multiple grading workflows in batch
    """
    check_database_service()
    start_time = time.time()
    results = []
    successful = 0
    failed = 0
    
    logger.info(f"Starting batch grading workflow for {len(requests)} requests")
    
    for grading_request in requests:
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
        "total_processed": len(requests),
        "total_successful": successful,
        "total_failed": failed,
        "total_processing_time_ms": total_time
    }


# Individual Workflow Steps

@router.get("/questions/{question_id}")
async def get_question(question_id: str) -> Dict[str, Any]:
    """Step 1: Retrieve ideal answer and marks for a question"""
    check_database_service()
    
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


@router.post("/questions/{question_id}/extract-concepts")
async def extract_and_save_concepts(question_id: str) -> Dict[str, Any]:
    """Step 2: Extract key concepts from ideal answer and save to database"""
    check_database_service()
    
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


@router.get("/students/{student_id}/answers/{question_id}")
async def get_student_answer(student_id: str, question_id: str) -> Dict[str, Any]:
    """Step 3: Retrieve student's submitted answer"""
    check_database_service()
    
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

@router.get("/students/{student_id}/results")
async def get_student_results(student_id: str) -> Dict[str, Any]:
    """Get all grading results for a student"""
    check_database_service()
    
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

@router.get("/info")
async def get_database_info() -> Dict[str, Any]:
    """Get database connection information"""
    return {
        "server": settings.db_server,
        "port": settings.db_port,
        "database": settings.db_name,
        "driver": settings.db_driver,
        "connected": db_manager is not None
    }



@router.get("/health")
async def database_health_check() -> Dict[str, Any]:
    """Check database connectivity"""
    
    check_database_service()
    if not db_manager:
        return {
            "status": "not_configured",
            "connected": False,
            "message": "Database not configured"
        }
    
    try:
        session = db_manager.get_session()
        session.execute("SELECT GETDATE()") # type: ignore
        session.close()
        
        return {
            "status": "healthy",
            "connected": True,
            "server": settings.db_server,
            "database": settings.db_name
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
        
        
########################################################################
# Note: The database services not needed for me

# @router.post("/questions")
# async def create_question(request: CreateQuestionRequest) -> Dict[str, Any]:
#     """Create a new question with ideal answer"""
#     check_database_service()
    
#     try:
#         question = database_service.create_question(
#             question_id=request.question_id,
#             subject=request.subject,
#             topic=request.topic,
#             question_text=request.question_text,
#             ideal_answer=request.ideal_answer,
#             max_marks=request.max_marks,
#             passing_threshold=request.passing_threshold,
#             difficulty_level=request.difficulty_level
#         )
        
#         return {
#             "id": question.id,
#             "question_id": question.question_id,
#             "subject": question.subject,
#             "topic": question.topic,
#             "max_marks": question.max_marks,
#             "created_at": question.created_at.isoformat(),
#             "message": f"Question {request.question_id} created successfully"
#         }
        
#     except Exception as e:
#         logger.error(f"Error creating question: {e}")
#         raise HTTPException(status_code=400, detail=str(e))


# @router.post("/student-answers")
# async def create_student_answer(request: CreateStudentAnswerRequest) -> Dict[str, Any]:
#     """Create a new student answer"""
#     check_database_service()
    
#     try:
#         student_answer = database_service.create_student_answer(
#             student_id=request.student_id,
#             question_id=request.question_id,
#             answer_text=request.answer_text,
#             language=request.language
#         )
        
#         return {
#             "id": student_answer.id,
#             "answer_id": student_answer.answer_id,
#             "student_id": student_answer.student_id,
#             "question_id": request.question_id,
#             "word_count": student_answer.word_count,
#             "submitted_at": student_answer.submitted_at.isoformat(),
#             "message": f"Student answer created successfully"
#         }
        
#     except Exception as e:
#         logger.error(f"Error creating student answer: {e}")
#         raise HTTPException(status_code=400, detail=str(e))
########################################################################