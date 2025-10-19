"""
Database Operations Router
Handles all MSSQL database-related endpoints and workflow
"""
import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...models.question import DatabaseManager
from ...services.question_service import QuestionService


logger = logging.getLogger(__name__)

# Router for database operations
router = APIRouter(
    prefix="/grade",
    tags=["Grade Operations"],
    responses={404: {"description": "Not found"}},
)

# Global question service components (will be set from main app)
db_manager: DatabaseManager = None
question_service: QuestionService = None


def set_database_services(db_mgr: DatabaseManager, db_svc: QuestionService):
    """Set question services from main application"""
    global db_manager, question_service
    db_manager = db_mgr
    question_service = db_svc


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


def check_question_service():
    """Helper to check if question service is available"""
    if not question_service:
        raise HTTPException(
            status_code=503, 
            detail="Question service not available. Please configure MSSQL connection."
        )

@router.post("/workflow", response_model=GradingWorkflowResponse)
async def complete_grading_workflow(request: GradingWorkflowRequest) -> GradingWorkflowResponse:
    """
    Complete AI grading workflow with MSSQL database:
    1. Retrieve ideal answer and marks from database
    2. Extract and save semantic understanding (key concepts) in database  
    3. Retrieve student's submitted answer from database
    4. Grade and save results in required format
    
    Returns exactly: {"Score": "X/10", "Justification": "...", "Key_Concepts_Covered": ["Concept A (2/3 points) - Reason..."]}
    """
    check_question_service()
    start_time = time.time()
    
    try:
        logger.info(f"Starting grading workflow for student {request.student_id}, question {request.question_id}")
        
        # Execute the complete workflow
        result = await question_service.complete_grading_workflow(
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


@router.post("/batch/workflow")
async def batch_grading_workflow(requests: List[GradingWorkflowRequest]) -> Dict[str, Any]:
    """
    Process multiple grading workflows in batch
    """
    check_question_service()
    start_time = time.time()
    results = []
    successful = 0
    failed = 0
    
    logger.info(f"Starting batch grading workflow for {len(requests)} requests")
    
    for grading_request in requests:
        request_start = time.time()
        try:
            result = await question_service.complete_grading_workflow(
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
