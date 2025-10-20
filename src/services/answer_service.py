"""
Answer Service for Student Answer Operations
Handles student answer CRUD operations and related functionality
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..utils.database_manager import DatabaseManager
from ..models.db_schemas import (
    Question, StudentAnswer, GradingResult, AuditLog
)

logger = logging.getLogger(__name__)


class AnswerService:
    """Answer service for student answer operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    def log_audit_event(self, session: Session, event_type: str, entity_type: str, 
                       entity_id: str, event_data: Dict[str, Any], 
                       result_status: str = "success", error_message: str = None): # type: ignore
        """Log audit event"""
        try:
            audit_log = AuditLog(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                event_data=json.dumps(event_data),
                result_status=result_status,
                error_message=error_message
            )
            session.add(audit_log)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def get_student_answer(self, student_id: str, question_id: str) -> Optional[StudentAnswer]:
        """
        Get student's submitted answer
        
        Args:
            student_id: Student identifier
            question_id: Question identifier
            
        Returns:
            StudentAnswer object or None if not found
        """
        session = self.get_session()
        try:
            # Join with Question to get question by question_id
            student_answer = session.query(StudentAnswer).join(Question).filter(
                StudentAnswer.student_id == student_id,
                Question.question_id == question_id
            ).first()
            
            if student_answer:
                # Update word count if not set
                if not student_answer.word_count:
                    student_answer.word_count = len(student_answer.answer_text.split())
                    session.commit()
                
                logger.info(f"Retrieved answer from student {student_id} for question {question_id}")
                
                # Log audit event
                self.log_audit_event(
                    session, "student_answer_retrieval", "student_answer", str(student_answer.id),
                    {
                        "student_id": student_id,
                        "question_id": question_id,
                        "word_count": student_answer.word_count
                    }
                )
            
            return student_answer
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving student answer: {e}")
            self.log_audit_event(
                session, "student_answer_retrieval", "student_answer", "unknown",
                {"student_id": student_id, "question_id": question_id}, "failure", str(e)
            )
            return None
        finally:
            session.close()
    
    def get_all_student_answers(self) -> List[Dict[str, Any]]:
        """
        Get all student answers from the database
        
        Returns:
            List of student answer dictionaries
        """
        session = self.get_session()
        try:
            # Query with join to get question details
            answers = session.query(StudentAnswer, Question).join(
                Question, StudentAnswer.question_id == Question.id
            ).all()
            
            result = []
            for student_answer, question in answers:
                result.append({
                    "id": student_answer.id,
                    "answer_id": student_answer.answer_id,
                    "student_id": student_answer.student_id,
                    "question_id": question.question_id,
                    "question_text": question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
                    "answer_text": student_answer.answer_text,
                    "word_count": student_answer.word_count,
                    "submitted_at": student_answer.submitted_at.isoformat(),
                    "language": student_answer.language
                })
            
            logger.info(f"Retrieved {len(result)} student answers")
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving student answers: {e}")
            return []
        finally:
            session.close()
    
    def get_student_answers_by_student(self, student_id: str) -> List[Dict[str, Any]]:
        """
        Get all answers for a specific student
        
        Args:
            student_id: Student identifier
            
        Returns:
            List of student answer dictionaries
        """
        session = self.get_session()
        try:
            # Query with join to get question details
            answers = session.query(StudentAnswer, Question).join(
                Question, StudentAnswer.question_id == Question.id
            ).filter(StudentAnswer.student_id == student_id).all()
            
            result = []
            for student_answer, question in answers:
                result.append({
                    "id": student_answer.id,
                    "answer_id": student_answer.answer_id,
                    "student_id": student_answer.student_id,
                    "question_id": question.question_id,
                    "question_text": question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
                    "answer_text": student_answer.answer_text,
                    "word_count": student_answer.word_count,
                    "submitted_at": student_answer.submitted_at.isoformat(),
                    "language": student_answer.language
                })
            
            logger.info(f"Retrieved {len(result)} answers for student {student_id}")
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving answers for student {student_id}: {e}")
            return []
        finally:
            session.close()
    
