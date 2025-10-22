"""
Answer Service for Student Answer Operations
Handles student answer CRUD operations and related functionality (raw SQL)
"""
import json
import logging
from typing import List, Dict, Any, Optional
from types import SimpleNamespace
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.utils.database_manager import DatabaseManager
from src.models.answer_model import IdealAnswer, StudentAnswer

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
            sql = text("""
                    SELECT question_id, subject, ideal_answer, max_marks 
                    FROM Question_Bank
                    WHERE ideal_answer IS NOT NULL
                    ORDER BY question_id DESC
                    """)
            rows = session.execute(sql).fetchall()
            
            result: List[IdealAnswer] = []
            for row in rows:
                m = row._mapping if hasattr(row, "_mapping") else row
                result.append(IdealAnswer(
                    question_id=m["question_id"],
                    subject=m["subject"],
                    ideal_answer=m["ideal_answer"],
                    max_marks=m["max_marks"]
                ))
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
            sql = text(
                """
                    SELECT question_id, subject, ideal_answer, max_marks 
                    FROM Question_Bank
                    WHERE question_id = :question_id AND ideal_answer IS NOT NULL
                    ORDER BY question_id DESC
                """
            )
            row = session.execute(sql, {"question_id": question_id}).fetchone()
            
            if not row:
                return None
                
            m = row._mapping if hasattr(row, "_mapping") else row
            result = IdealAnswer(
                question_id=m["question_id"],
                subject=m["subject"],
                ideal_answer=m["ideal_answer"],
                max_marks=m["max_marks"]
            )
            logger.info(f"Retrieved ideal answer for question {question_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving ideal answer for question {question_id}: {e}")
            return None
        finally:
            session.close()
    
    
    async def get_all_student_answers(self) -> List[StudentAnswer]:
        """Get all student answers from the database as a list of StudentAnswer models"""
        session = self.get_session()
        student_answers: List[StudentAnswer] = []

        try:
            # Fetch all student answer rows ordered by answer_id
            sql = text(
                """
                SELECT a.answer_id,a.student_id,a.question_id,q.subject,q.topic,q.question_text,a.answer_text,a.language,a.word_count,q.max_marks,q.passing_threshold
                FROM Student_Answers a
                INNER JOIN Question_Bank q ON a.question_id = q.question_id
                ORDER BY a.answer_id DESC
                """
            )
            rows = session.execute(sql).fetchall()

            for row in rows:
                sa = _row_to_ns(row)
                # Convert SQL row → Pydantic model
                student_answer = StudentAnswer(
                    answer_id=sa.answer_id,
                    student_id=sa.student_id,
                    question_id=sa.question_id,
                    subject=sa.subject,
                    topic=sa.topic,
                    question_text=sa.question_text,
                    answer_text=sa.answer_text,
                    language=sa.language,
                    word_count=sa.word_count,
                    max_marks=sa.max_marks,
                    passing_threshold=sa.passing_threshold
                )
                student_answers.append(student_answer)

            logger.info(f"Retrieved {len(student_answers)} student answers")
            return student_answers

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all student answers: {e}")
            return []

        finally:
            session.close()
    
    
    async def get_student_answer(self, student_id: int, question_id: int) -> StudentAnswer:
        """Get student's submitted answer via direct SQL"""
        session = self.get_session()
        try:
            sql = text(
                """
                SELECT a.answer_id,a.student_id,a.question_id,q.subject,q.topic,q.question_text,a.answer_text,a.language,a.word_count,q.max_marks,q.passing_threshold
                FROM Student_Answers a
                INNER JOIN Question_Bank q ON a.question_id = q.question_id
                WHERE a.student_id = :student_id AND a.question_id = :question_id
                ORDER BY a.answer_id DESC
                """
            )
            row = session.execute(sql, {"student_id": student_id, "question_id": question_id}).fetchone()
            
            if not row:
                return None
            sa = row._mapping if hasattr(row, "_mapping") else row
            
            ##### Update word count if not set
            if not sa["word_count"]:
                wc = len((sa["answer_text"] or "").split())
                session.execute(text("UPDATE Student_Answers SET word_count = :wc WHERE id = :id"), {"wc": wc, "id": sa["id"]})
                session.commit()
                sa = dict(sa)
                sa["word_count"] = wc
            
            logger.info(f"Retrieved answer from student {student_id} for question {question_id}")
            
            # Return a simple namespace-like dict access via attribute in routers
            return type("Obj", (), sa) if isinstance(sa, dict) else sa
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving student answer: {e}")
            return None
        finally:
            session.close()
    
    async def submit_student_answer(self, student_id: int, question_id: int, answer_text: str, language: str = "en") -> StudentAnswer:
        """Insert a new student answer and return the joined StudentAnswer model"""
        if not answer_text or not str(answer_text).strip():
            raise ValueError("answer_text is required")

        session = self.get_session()
        try:
            # Ensure the question exists and fetch question details for response mapping
            q_row = session.execute(text(
                """
                SELECT question_id, subject, topic, question_text, max_marks, passing_threshold
                FROM Question_Bank
                WHERE question_id = :qid
                """
            ), {"qid": question_id}).fetchone()
            if not q_row:
                raise ValueError(f"Question {question_id} not found")

            # Compute word count
            word_count = len(answer_text.split())

            # Insert answer and get new answer_id
            insert_sql = text(
                """
                INSERT INTO Student_Answers (student_id, question_id, answer_text, language, word_count, submitted_at)
                OUTPUT INSERTED.answer_id
                VALUES (:student_id, :question_id, :answer_text, :language, :word_count, GETUTCDATE())
                """
            )
            inserted = session.execute(insert_sql, {
                "student_id": student_id,
                "question_id": question_id,
                "answer_text": answer_text,
                "language": language,
                "word_count": word_count,
            }).fetchone()
            session.commit()

            new_answer_id = inserted[0] if inserted else None

            # Retrieve the full joined row as returned by other getters
            row = session.execute(text(
                """
                SELECT a.answer_id,a.student_id,a.question_id,q.subject,q.topic,q.question_text,a.answer_text,a.language,a.word_count,q.max_marks,q.passing_threshold
                FROM Student_Answers a
                INNER JOIN Question_Bank q ON a.question_id = q.question_id
                WHERE a.answer_id = :aid
                """
            ), {"aid": new_answer_id}).fetchone()

            if not row:
                # Fallback: construct from question + provided fields
                m = q_row._mapping if hasattr(q_row, "_mapping") else q_row
                return StudentAnswer(
                    answer_id=new_answer_id or 0,
                    student_id=student_id,
                    question_id=question_id,
                    subject=m["subject"],
                    topic=m["topic"],
                    question_text=m["question_text"],
                    answer_text=answer_text,
                    language=language,
                    word_count=word_count,
                    max_marks=m["max_marks"],
                    passing_threshold=m["passing_threshold"],
                )

            m = row._mapping if hasattr(row, "_mapping") else row
            result = StudentAnswer(
                answer_id=m["answer_id"],
                student_id=m["student_id"],
                question_id=m["question_id"],
                subject=m["subject"],
                topic=m["topic"],
                question_text=m["question_text"],
                answer_text=m["answer_text"],
                language=m["language"],
                word_count=m["word_count"],
                max_marks=m["max_marks"],
                passing_threshold=m["passing_threshold"],
            )
            logger.info(f"Inserted student answer {result.answer_id} for student {student_id}, question {question_id}")
            return result

        except Exception as e:
            session.rollback()
            logger.error(f"Error submitting student answer: {e}")
            raise
        finally:
            session.close()
    
    
    async def get_student_answers_by_student(self, student_id: int) -> List[StudentAnswer]:
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