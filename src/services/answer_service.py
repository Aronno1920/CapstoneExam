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

from src.utils.database_manager import DatabaseManager
from src.models.question_model import Question
from src.models.answer_model import IdealAnswer, Answer

logger = logging.getLogger(__name__)


class AnswerService:
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    
############################################

    async def get_all_ideal_answers(self) -> List[IdealAnswer]:
        """Get all ideal answers from the database"""
        session = self.get_session()
        try:
            rows = session.execute(text(
                """
                    SELECT question_id, subject, ideal_answer, max_marks 
                    FROM Question_Bank
                    WHERE ideal_answer IS NOT NULL
                    ORDER BY question_id DESC
                """
            )).fetchall()
            result: List[IdealAnswer] = []
            for row in rows:
                m = row._mapping if hasattr(row, "_mapping") else row
                result.append({
                    "question_id": m["question_id"],
                    "subject": m["subject"],
                    "ideal_answer": m["ideal_answer"],
                    "max_marks": m["max_marks"]
                })
            logger.info(f"Retrieved {len(result)} ideal answers")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving ideal answers: {e}")
            return []
        finally:
            session.close()
    
    
    async def get_ideal_answer_by_question_id(self, question_id: int) -> IdealAnswer:
        """Get ideal answer for a specific question"""
        session = self.get_session()
        try:
            row = session.execute(text(
                """
                    SELECT question_id, subject, ideal_answer, max_marks 
                    FROM Question_Bank
                    WHERE question_id = :question_id AND ideal_answer IS NOT NULL
                    ORDER BY question_id DESC
                """
            ), {"question_id": question_id}).fetchone()
            
            if not row:
                return None
                
            m = row._mapping if hasattr(row, "_mapping") else row
            result = {
                    "question_id": m["question_id"],
                    "subject": m["subject"],
                    "ideal_answer": m["ideal_answer"],
                    "max_marks": m["max_marks"]
            }
            logger.info(f"Retrieved ideal answer for question {question_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving ideal answer for question {question_id}: {e}")
            return None
        finally:
            session.close()
    
    
    async def get_student_answer(self, student_id: int, question_id: int) -> Optional[Any]:
        """Get student's submitted answer via direct SQL"""
        session = self.get_session()
        try:
            sql = text(
                """
                SELECT sa.*
                FROM Student_Answers sa
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
    
    
    async def get_all_student_answers(self) -> List[Dict[str, Any]]:
        """Get all student answers from the database"""
        session = self.get_session()
        try:
            rows = session.execute(text(
                """
                SELECT sa.*, q.question_id, q.question_text
                FROM Student_Answers sa
                INNER JOIN questions q ON sa.question_id = q.id
                ORDER BY sa.submitted_at DESC
                """
            )).fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                m = row._mapping if hasattr(row, "_mapping") else row
                qt = m["question_text"] or ""
                result.append({
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
    
    
    async def get_student_answers_by_student(self, student_id: int) -> List[Dict[str, Any]]:
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

############################################