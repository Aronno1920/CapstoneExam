"""
Question Service for MSSQL Server Operations
Handles the specific workflow: retrieve ideal answer -> extract concepts -> retrieve student answer -> grade and save
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from types import SimpleNamespace
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..utils.database_manager import DatabaseManager
from src.models.question_model import Question

logger = logging.getLogger(__name__)


def _row_to_ns(row: Any) -> SimpleNamespace:
    """Convert SQLAlchemy Row to attribute-accessible namespace"""
    if row is None:
        return None  # type: ignore
    try:
        mapping = row._mapping  # SQLAlchemy 1.4/2.0 RowMapping
        return SimpleNamespace(**dict(mapping))
    except AttributeError:
        return SimpleNamespace(**dict(row))


class QuestionService:

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()


###########################################

    async def get_question_by_id(self, question_id: int) -> Optional[Question]:
        session = self.get_session()
        try:
            q_sql = text("SELECT TOP 1 * FROM Question_Bank WHERE question_id = :qid")
            row = session.execute(q_sql, {"qid": question_id}).fetchone()
            if not row:
                return None

            # Convert SQLAlchemy row to object-like namespace
            question = _row_to_ns(row)

            # Count associated key concepts
            count_sql = text("SELECT COUNT(*) AS cnt FROM Question_KeyConcept WHERE question_id = :qid")
            cnt_row = session.execute(count_sql, {"qid": question.question_id}).fetchone()
            key_concepts_count = cnt_row[0] if cnt_row else 0

            # Build and return model instance
            result = Question(
                question_id=question.question_id,
                subject=question.subject,
                topic=question.topic,
                question_text=question.question_text,
                ideal_answer=question.ideal_answer,
                max_marks=question.max_marks,
                passing_threshold=question.passing_threshold
            )

            logger.info(f"Retrieved question {question_id} with {key_concepts_count} key concepts")
            return result

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving question {question_id}: {e}")
            return None

        finally:
            session.close()
    
    
    async def get_all_questions(self) -> List[Question]:
        """Get all questions from the database as a list of Question models"""
        session = self.get_session()
        questions: List[Question] = []

        try:
            # Fetch all question rows ordered by creation time
            q_sql = text("SELECT * FROM Question_Bank ORDER BY Question_ID DESC")
            rows = session.execute(q_sql).fetchall()

            for row in rows:
                q = _row_to_ns(row)
                # Convert SQL row → Pydantic model
                question = Question(
                    question_id=q.question_id,
                    subject=q.subject,
                    topic=q.topic,
                    question_text=q.question_text,
                    ideal_answer=getattr(q, "ideal_answer", ""),  # optional if not in select
                    max_marks=q.max_marks,
                    passing_threshold=q.passing_threshold
                )
                questions.append(question)

            logger.info(f"Retrieved {len(questions)} questions")
            return questions

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all questions: {e}")
            return []

        finally:
            session.close()
    

    async def create_question(self, question_id: int, subject: str, topic: str, 
                       question_text: str, ideal_answer: str, max_marks: float,
                       passing_threshold: float = 60.0, difficulty_level: str = "intermediate") -> SimpleNamespace:
        """Create a new question with ideal answer (raw SQL)"""
        session = self.get_session()
        try:
            row = session.execute(text(
                """
                INSERT INTO Question_Bank (
                    question_id, subject, topic, question_text, ideal_answer, max_marks, passing_threshold
                )
                OUTPUT INSERTED.id
                VALUES (:question_id, :subject, :topic, :question_text, :ideal_answer, :max_marks, :passing_threshold)
                """
            ), {
                "question_id": question_id,
                "subject": subject,
                "topic": topic,
                "question_text": question_text,
                "ideal_answer": ideal_answer,
                "max_marks": max_marks,
                "passing_threshold": passing_threshold,
            }).fetchone()
            qid = row[0] if row else None
            sel = session.execute(text("SELECT * FROM Question_Bank WHERE question_id = :id"), {"id": qid}).fetchone()
            session.commit()
            logger.info(f"Created question {question_id}")
            return _row_to_ns(sel)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating question {question_id}: {e}")
            raise
        finally:
            session.close()
    
    
    async def create_student_answer(self, student_id: int, question_id: int, 
                            answer_text: str, language: str = "en") -> SimpleNamespace:
        """Create a new student answer (raw SQL)"""
        session = self.get_session()
        try:
            qrow = session.execute(text("SELECT id FROM Question_Bank WHERE question_id = :qid"), {"qid": question_id}).fetchone()
            if not qrow:
                raise ValueError(f"Question {question_id} not found")
            qid = qrow[0]
            wc = len((answer_text or "").split())
            row = session.execute(text(
                """
                INSERT INTO Student_Answers (
                    answer_id, student_id, question_id, answer_text, language, word_count, submitted_at
                )
                OUTPUT INSERTED.id
                VALUES (:answer_id, :student_id, :question_id, :answer_text, :language, :word_count, GETUTCDATE())
                """
            ), {
                "answer_id": str(uuid.uuid4()),
                "student_id": student_id,
                "question_id": qid,
                "answer_text": answer_text,
                "language": language,
                "word_count": wc,
            }).fetchone()
            aid = row[0] if row else None
            sel = session.execute(text("SELECT * FROM Student_Answers WHERE id = :id"), {"id": aid}).fetchone()
            session.commit()
            logger.info(f"Created student answer for {student_id}, question {question_id}")
            return _row_to_ns(sel)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating student answer: {e}")
            raise
        finally:
            session.close()
    

    async def get_grading_results_by_student(self, student_id: int) -> List[Dict[str, Any]]:
        """Get all grading results for a student (raw SQL)"""
        session = self.get_session()
        try:
            rows = session.execute(text(
                """
                SELECT gr.*
                FROM grading_results gr
                INNER JOIN Student_Answers sa ON gr.student_answer_id = sa.id
                WHERE sa.student_id = :student_id
                ORDER BY gr.graded_at DESC
                """
            ), {"student_id": student_id}).fetchall()
            formatted_results: List[Dict[str, Any]] = []
            for row in rows:
                formatted_results.append(self._format_grading_response_raw(_row_to_ns(row), session))
            return formatted_results
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving grading results for student {student_id}: {e}")
            return []
        finally:
            session.close()

###########################################

