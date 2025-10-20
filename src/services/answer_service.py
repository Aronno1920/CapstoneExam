"""
Answer Service for Student Answer Operations
Handles student answer CRUD operations and related functionality (raw SQL)
"""
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..utils.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AnswerService:
    """Answer service for student answer operations using direct queries"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    def get_student_answer(self, student_id: str, question_id: str) -> Optional[Any]:
        """Get student's submitted answer via direct SQL"""
        session = self.get_session()
        try:
            sql = text(
                """
                SELECT sa.*
                FROM student_answers sa
                INNER JOIN questions q ON sa.question_id = q.id
                WHERE sa.student_id = :student_id AND q.question_id = :question_id
                """
            )
            row = session.execute(sql, {"student_id": student_id, "question_id": question_id}).fetchone()
            if not row:
                return None
            sa = row._mapping if hasattr(row, "_mapping") else row
            
            # Update word count if not set
            # if not sa["word_count"]:
            #     wc = len((sa["answer_text"] or "").split())
            #     session.execute(text("UPDATE student_answers SET word_count = :wc WHERE id = :id"), {"wc": wc, "id": sa["id"]})
            #     session.commit()
            #     sa = dict(sa)
            #     sa["word_count"] = wc
            
            logger.info(f"Retrieved answer from student {student_id} for question {question_id}")
            
            # Return a simple namespace-like dict access via attribute in routers
            return type("Obj", (), sa) if isinstance(sa, dict) else sa
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving student answer: {e}")
            return None
        finally:
            session.close()
    
    def get_all_student_answers(self) -> List[Dict[str, Any]]:
        """Get all student answers from the database"""
        session = self.get_session()
        try:
            rows = session.execute(text(
                """
                SELECT sa.*, q.question_id, q.question_text
                FROM student_answers sa
                INNER JOIN questions q ON sa.question_id = q.id
                ORDER BY sa.submitted_at DESC
                """
            )).fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                m = row._mapping if hasattr(row, "_mapping") else row
                qt = m["question_text"] or ""
                result.append({
                    "id": m["id"],
                    "answer_id": m["answer_id"],
                    "student_id": m["student_id"],
                    "question_id": m["question_id"],
                    "question_text": qt[:100] + ("..." if len(qt) > 100 else ""),
                    "answer_text": m["answer_text"],
                    "word_count": m["word_count"],
                    "submitted_at": m["submitted_at"].isoformat() if m["submitted_at"] else None,
                    "language": m["language"],
                })
            logger.info(f"Retrieved {len(result)} student answers")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving student answers: {e}")
            return []
        finally:
            session.close()
    
    def get_student_answers_by_student(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all answers for a specific student"""
        session = self.get_session()
        try:
            rows = session.execute(text(
                """
                SELECT sa.*, q.question_id, q.question_text
                FROM student_answers sa
                INNER JOIN questions q ON sa.question_id = q.id
                WHERE sa.student_id = :student_id
                ORDER BY sa.submitted_at DESC
                """
            ), {"student_id": student_id}).fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                m = row._mapping if hasattr(row, "_mapping") else row
                qt = m["question_text"] or ""
                result.append({
                    "id": m["id"],
                    "answer_id": m["answer_id"],
                    "student_id": m["student_id"],
                    "question_id": m["question_id"],
                    "question_text": qt[:100] + ("..." if len(qt) > 100 else ""),
                    "answer_text": m["answer_text"],
                    "word_count": m["word_count"],
                    "submitted_at": m["submitted_at"].isoformat() if m["submitted_at"] else None,
                    "language": m["language"],
                })
            logger.info(f"Retrieved {len(result)} answers for student {student_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving answers for student {student_id}: {e}")
            return []
        finally:
            session.close()
    
