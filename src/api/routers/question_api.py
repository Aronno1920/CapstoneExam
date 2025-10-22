"""
Question Operations Router: Handles all MSSQL question-related endpoints and workflow
"""
import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from urllib.parse import quote_plus
from sqlalchemy import text

from src.models.question_model import Question
from src.utils.database_manager import DatabaseManager
from src.services.question_service import QuestionService
from src.services.rag_service import RAGService
from src.utils.config import settings

logger = logging.getLogger(__name__)

# Router for question operations
router = APIRouter(
    prefix="/question",
    tags=["Question Operations"],
    responses={404: {"description": "Not found"}},
)

# Global question service components (will be set from main app)
ndb_manager: DatabaseManager = None  # type: ignore
question_service: QuestionService = None # type: ignore
rag_service: RAGService = None # type: ignore


def set_database_services(db_mgr: DatabaseManager, qus_svc: QuestionService):
    """Set question services from main application"""
    global ndb_manager, question_service, rag_service
    ndb_manager = db_mgr
    question_service = qus_svc
    rag_service = RAGService(db_mgr)

def check_question_service():
    """Ensure question service is available; lazily initialize if missing or dead"""
    global ndb_manager, question_service, rag_service

    if question_service and ndb_manager and rag_service:
        try:
            session = ndb_manager.get_session()
            try:
                session.execute(text("SELECT 1"))
                return
            finally:
                session.close()
        except Exception:
            question_service = None # type: ignore
            rag_service = None # type: ignore
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
        question_service = QuestionService(ndb_manager)
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

################################################

@router.get("/all")
async def get_all_questions() -> List[Question]:
    """Get all questions from the database"""
    check_question_service()
    
    try:
        questions = await question_service.get_all_questions()
        
        if not questions:
            raise HTTPException(status_code=404, detail=f"Questions not found")

        return questions
        
    except Exception as e:
        logger.error(f"Error retrieving all questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{question_id}")
async def get_question(question_id: int) -> Question:
    """Step 1: Retrieve ideal answer and marks for a question"""
    check_question_service()
    
    try:
        question_details = await question_service.get_question_by_id(question_id)
        if not question_details:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        return question_details
        
    except Exception as e:
        logger.error(f"Error retrieving question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/{question_id}")
async def get_question_concepts(question_id: int) -> Dict[str, Any]:
    """Get key concepts information for a specific question"""
    check_question_service()
    
    try:
        # Get key concepts from database
        session = ndb_manager.get_session()
        try:
            sql = text("""
                SELECT key_id, concept_name, concept_description, importance_score, keywords, max_points, created_at
                FROM Question_KeyConcept 
                WHERE question_id = :question_id
                ORDER BY importance_score DESC, created_at ASC
            """)
            rows = session.execute(sql, {"question_id": question_id}).fetchall()
            
            if not rows:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No key concepts found for question {question_id}"
                )
            
            concepts_data = []
            for row in rows:
                concept_info = {
                    "key_id": row.key_id,
                    "concept_name": row.concept_name,
                    "concept_description": row.concept_description,
                    "importance_score": row.importance_score,
                    "keywords": row.keywords,
                    "max_points": row.max_points,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                }
                concepts_data.append(concept_info)
            
            return {
                "question_id": question_id,
                "concepts_count": len(concepts_data),
                "concepts": concepts_data,
                "total_max_points": sum(concept["max_points"] for concept in concepts_data),
                "status": "success"
            }
            
        finally:
            session.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving concepts for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-concepts/{question_id}")
async def extract_and_save_concepts(question_id: int) -> Dict[str, Any]:
    """Step 2: Extract key concepts from ideal answer and save to database"""
    check_question_service()
    
    try:
        question = rag_service.get_question_with_ideal_answer(question_id)
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        start_time = time.time()
        key_concepts = await rag_service.extract_and_save_key_concepts(question)
        processing_time = (time.time() - start_time) * 1000
        
        concepts_data = []
        for concept in key_concepts:
            concepts_data.append({
                "key_id": concept.key_id,
                "question_id": question_id,
                "concept_name": concept.concept_name,
                "concept_description": concept.concept_description,
                "importance_score": concept.importance_score,
                "keywords": concept.keywords,
                "max_points": concept.max_points,
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

################################################