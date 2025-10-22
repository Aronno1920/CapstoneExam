"""
Answer Operations Router
Handles all student answer-related endpoints
"""
import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from urllib.parse import quote_plus
from sqlalchemy import text

from src.models.question_model import Question
from src.models.answer_model import Answer, IdealAnswer, StudentAnswer

from src.utils.database_manager import DatabaseManager
from src.services.answer_service import AnswerService
from src.services.rag_service import RAGService
from src.utils.config import settings

logger = logging.getLogger(__name__)

# Router for answer operations
router = APIRouter(
    prefix="/answer",
    tags=["Answer Operations"],
    responses={404: {"description": "Not found"}},
)

# Global answer service components (will be set from main app)
ndb_manager: DatabaseManager = None  # type: ignore
answer_service: AnswerService = None # type: ignore
rag_service: RAGService = None # type: ignore


def set_database_services(db_mgr: DatabaseManager, ans_svc: AnswerService):
    """Set question services from main application"""
    global ndb_manager, answer_service, rag_service
    ndb_manager = db_mgr
    answer_service = ans_svc
    rag_service = RAGService(db_mgr)


def check_answer_service():
    """Ensure question service is available; lazily initialize if missing or dead"""
    global ndb_manager, answer_service, rag_service

    if answer_service and ndb_manager and rag_service:
        try:
            session = ndb_manager.get_session()
            try:
                session.execute(text("SELECT 1"))
                return
            finally:
                session.close()
        except Exception:
            answer_service = None
            rag_service = None
            ndb_manager = None  # type: ignore

    try:
        if settings.database_url and settings.database_url.strip():
            db_url = settings.database_url.strip()
        else:
            driver = quote_plus(settings.db_driver)
            if settings.use_windows_auth:
                db_url = (
                    f"mssql+pyodbc://@{settings.db_server},{settings.db_port}/"
                    f"{settings.db_name}?driver={driver}&trusted_connection=yes"
                )
            else:
                username = quote_plus(settings.db_username)
                password = quote_plus(settings.db_password)
                db_url = (
                    f"mssql+pyodbc://{username}:{password}@"
                    f"{settings.db_server},{settings.db_port}/{settings.db_name}?driver={driver}"
                )
        ndb_manager = DatabaseManager(db_url)
        answer_service = AnswerService(ndb_manager)
        rag_service = RAGService(ndb_manager)

        session = ndb_manager.get_session()
        try:
            session.execute(text("SELECT 1"))
        finally:
            session.close()

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Question service not available. Database init failed: {e}"
        )


############################################

@router.get("/ideal-answers")
async def get_all_ideal_answers() -> List[IdealAnswer]:
    """Get all ideal answers from the database"""
    check_answer_service()
    
    try:
        ideal_answers = await answer_service.get_all_ideal_answers()
        
        if not ideal_answers:
            raise HTTPException(status_code=404, detail="No ideal answers found")
        
        return ideal_answers
    
    except Exception as e:
        logger.error(f"Error retrieving all ideal answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ideal-answers/{question_id}")
async def get_ideal_answer_by_question(question_id: int) -> IdealAnswer:
    """Get ideal answer for a specific question"""
    check_answer_service()
    
    try:
        ideal_answer = await answer_service.get_ideal_answer_by_question_id(question_id)
        
        if not ideal_answer:
            raise HTTPException(status_code=404, detail=f"Ideal answer not found for question {question_id}")
            
        return ideal_answer
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ideal answer for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_student_answers() -> List[StudentAnswer]:
    """Get all student answers from the database"""
    check_answer_service()
    
    try:
        answers = await answer_service.get_all_student_answers()
        
        if not answers:
            raise HTTPException(status_code=404, detail=f"Student answer not found for question {answers}")
            
        return answers
        
    except Exception as e:
        logger.error(f"Error retrieving all student answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}")
async def get_student_answers(student_id: int) -> List[StudentAnswer]:
    """Get all answers for a specific student"""
    check_answer_service()
    
    try:
        answers = await answer_service.get_student_answers_by_student(student_id)
        
        if not answers:
            raise HTTPException(status_code=404, detail=f"Student answer not found for question {answers}")
            
        return answers
        
    except Exception as e:
        logger.error(f"Error retrieving answers for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}/question/{question_id}")
async def get_student_answer(student_id: int, question_id: int) -> StudentAnswer:
    """Get student's answer for a specific question"""
    check_answer_service()
    
    try:
        student_answer = await answer_service.get_student_answer(student_id, question_id)
        
        if not student_answer:
            raise HTTPException(status_code=404, detail=f"Student answer not found for student {student_id}, question {question_id}")
        
        return student_answer
        
    except Exception as e:
        logger.error(f"Error retrieving student answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Statistics and Utility Endpoints
@router.get("/stats")
async def get_answer_statistics() -> Dict[str, Any]:
    """Get statistics about student answers"""
    check_answer_service()
    
    try:
        all_answers = await answer_service.get_all_student_answers()
        
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

############################################