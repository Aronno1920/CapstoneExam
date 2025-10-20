"""
Answer Operations Router
Handles all student answer-related endpoints
"""
import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...services.answer_service import AnswerService

logger = logging.getLogger(__name__)

# Router for answer operations
router = APIRouter(
    prefix="/answer",
    tags=["Answer Operations"],
    responses={404: {"description": "Not found"}},
)

# Global answer service components (will be set from main app)
answer_service: AnswerService = None # type: ignore


def set_database_services(ans_svc: AnswerService):
    """Set answer services from main application"""
    global answer_service
    answer_service = ans_svc


# Request/Response Models

def check_answer_service():
    """Helper to check if answer service is available"""
    if not answer_service:
        raise HTTPException(
            status_code=503, 
            detail="Answer service not available. Please configure MSSQL connection."
        )


# Answer CRUD Operations
@router.get("/all")
async def get_all_student_answers() -> Dict[str, Any]:
    """Get all student answers from the database"""
    check_answer_service()
    
    try:
        answers = answer_service.get_all_student_answers()
        
        return {
            "student_answers": answers,
            "total_count": len(answers),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving all student answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}")
async def get_student_answers(student_id: str) -> Dict[str, Any]:
    """Get all answers for a specific student"""
    check_answer_service()
    
    try:
        answers = answer_service.get_student_answers_by_student(student_id)
        
        return {
            "student_id": student_id,
            "student_answers": answers,
            "total_count": len(answers),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving answers for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}/question/{question_id}")
async def get_student_answer(student_id: str, question_id: str) -> Dict[str, Any]:
    """Get student's answer for a specific question"""
    check_answer_service()
    
    try:
        student_answer = answer_service.get_student_answer(student_id, question_id)
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



# Statistics and Utility Endpoints
@router.get("/stats")
async def get_answer_statistics() -> Dict[str, Any]:
    """Get statistics about student answers"""
    check_answer_service()
    
    try:
        all_answers = answer_service.get_all_student_answers()
        
        # Calculate basic statistics
        total_answers = len(all_answers)
        if total_answers == 0:
            return {
                "total_answers": 0,
                "unique_students": 0,
                "unique_questions": 0,
                "average_word_count": 0,
                "status": "success"
            }
        
        unique_students = len(set(answer["student_id"] for answer in all_answers))
        unique_questions = len(set(answer["question_id"] for answer in all_answers))
        average_word_count = sum(answer["word_count"] or 0 for answer in all_answers) / total_answers
        
        return {
            "total_answers": total_answers,
            "unique_students": unique_students,
            "unique_questions": unique_questions,
            "average_word_count": round(average_word_count, 2),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error calculating answer statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
