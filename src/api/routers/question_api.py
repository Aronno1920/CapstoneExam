"""
Question Operations Router: Handles all MSSQL question-related endpoints and workflow
"""
import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...services.question_service import QuestionService

logger = logging.getLogger(__name__)

# Router for question operations
router = APIRouter(
    prefix="/question",
    tags=["Question Operations"],
    responses={404: {"description": "Not found"}},
)

# Global question service components (will be set from main app)
question_service: QuestionService = None # type: ignore


def set_database_services(db_svc: QuestionService):
    """Set question services from main application"""
    global question_service
    question_service = db_svc

def check_question_service():
    """Helper to check if question service is available"""
    if not question_service:
        raise HTTPException(
            status_code=503, 
            detail="Question service not available. Please configure MSSQL connection."
        )

# Database Info and Health Check Endpoints
@router.get("/{question_id}")
async def get_question(question_id: str) -> Dict[str, Any]:
    """Step 1: Retrieve ideal answer and marks for a question"""
    check_question_service()
    
    try:
        question_details = question_service.get_question_details(question_id)
        if not question_details:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        return question_details
        
    except Exception as e:
        logger.error(f"Error retrieving question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_questions() -> Dict[str, Any]:
    """Get all questions from the database"""
    check_question_service()
    
    try:
        questions = question_service.get_all_questions()
        
        return {
            "questions": questions,
            "total_count": len(questions),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving all questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}/answers/{question_id}")
async def get_student_answer(student_id: str, question_id: str) -> Dict[str, Any]:
    """Step 3: Retrieve student's submitted answer"""
    check_question_service()
    
    try:
        student_answer = question_service.get_student_answer(student_id, question_id)
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


@router.get("/students/{student_id}/results")
async def get_student_results(student_id: str) -> Dict[str, Any]:
    """Get all grading results for a student"""
    check_question_service()
    
    try:
        results = question_service.get_grading_results_by_student(student_id)
        return {
            "student_id": student_id,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error retrieving results for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/questions/{question_id}/extract-concepts")
async def extract_and_save_concepts(question_id: str) -> Dict[str, Any]:
    """Step 2: Extract key concepts from ideal answer and save to database"""
    check_question_service()
    
    try:
        question = question_service.get_question_with_ideal_answer(question_id)
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        start_time = time.time()
        key_concepts = await question_service.extract_and_save_key_concepts(question)
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
