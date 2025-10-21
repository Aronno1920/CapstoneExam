"""
RAG (Retrieval-Augmented Generation) Service for AI Examiner System
Handles question retrieval, key concept extraction, and student answer processing
"""
import json
import uuid
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from types import SimpleNamespace
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..utils.database_manager import DatabaseManager
from .llm_service import llm_service
from ..utils.config import settings

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


class RAGService:
    """RAG Service for handling question retrieval, concept extraction, and student answer processing"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    # Step 1: Retrieve Ideal Answer and Marks
    def get_question_with_ideal_answer(self, question_id: str) -> Optional[SimpleNamespace]:
        """
        Step 1: Retrieve ideal answer and marks for a question
        
        Args:
            question_id: Unique identifier for the question
            
        Returns:
            Object with question fields, or None if not found
        """
        session = self.get_session()
        try:
            sql = text("SELECT TOP 1 * FROM questions WHERE question_id = :qid")
            row = session.execute(sql, {"qid": question_id}).fetchone()
            question = _row_to_ns(row)
            
            if question:
                logger.info(f"Retrieved question {question_id}")
                
            return question
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving question {question_id}: {e}")
            return None
        finally:
            session.close()
    
    # Step 2: Save Semantic Understanding (Key Concepts)
    async def extract_and_save_key_concepts(self, question: SimpleNamespace) -> List[SimpleNamespace]:
        """
        Step 2: Extract key concepts from ideal answer and save to database
        """
        session = self.get_session()
        try:
            # Check if concepts already exist
            exist_rows = session.execute(
                text("SELECT * FROM key_concepts WHERE question_id = :qid"),
                {"qid": question.id}
            ).fetchall()
            if exist_rows:
                concepts = [_row_to_ns(r) for r in exist_rows]
                logger.info(f"Using existing {len(concepts)} key concepts for question {question.question_id}")
                return concepts
            
            # Extract key concepts using LLM
            logger.info(f"Extracting key concepts for question {question.question_id}")
            concepts_data = await llm_service.extract_key_concepts(
                question.ideal_answer,
                question.subject,
                question.topic
            )
            
            # Calculate points per concept (distribute total marks)
            points_per_concept = question.max_marks / len(concepts_data) if concepts_data else 0
            
            # Save concepts to database with OUTPUT to get inserted IDs
            saved_concepts: List[SimpleNamespace] = []
            insert_sql = text(
                """
                INSERT INTO key_concepts (
                    question_id, concept_name, concept_description, importance_score, keywords, max_points, extraction_method, created_at
                )
                OUTPUT INSERTED.id
                VALUES (
                    :question_id, :concept_name, :concept_description, :importance_score, :keywords, :max_points, :extraction_method, :created_at
                )
                """
            )
            now = datetime.utcnow()
            for concept_data in concepts_data:
                params = {
                    "question_id": question.id,
                    "concept_name": concept_data["concept"],
                    "concept_description": concept_data["explanation"],
                    "importance_score": concept_data["importance"],
                    "keywords": json.dumps(concept_data.get("keywords", [])),
                    "max_points": points_per_concept,
                    "extraction_method": "llm_extracted",
                    "created_at": now,
                }
                inserted = session.execute(insert_sql, params).fetchone()
                new_id = inserted[0] if inserted else None
                saved_concepts.append(SimpleNamespace(id=new_id, **params))
            session.commit()
            
            logger.info(f"Saved {len(saved_concepts)} key concepts for question {question.question_id}")
            
            return saved_concepts
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error extracting/saving key concepts for question {question.question_id}: {e}")
            
            raise
        finally:
            session.close()
    
    # Step 3: Retrieve Student's Submitted Answer
    def get_student_answer(self, student_id: str, question_id: str) -> Optional[SimpleNamespace]:
        """Retrieve student's submitted answer via direct SQL"""
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
            sa = _row_to_ns(row)
            
            # Update word count if not set
            if getattr(sa, "word_count", None) in (None, 0):
                wc = len((sa.answer_text or "").split())
                session.execute(text("UPDATE student_answers SET word_count = :wc WHERE id = :id"), {"wc": wc, "id": sa.id})
                session.commit()
                sa.word_count = wc
            
            logger.info(f"Retrieved answer from student {student_id} for question {question_id}")
            
            return sa
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving student answer: {e}")
            return None
        finally:
            session.close()
    
    # Step 4: Grade and Save Results
    async def grade_and_save_result(
        self, 
        question: SimpleNamespace, 
        student_answer: SimpleNamespace, 
        key_concepts: List[SimpleNamespace]
    ) -> Dict[str, Any]:
        """
        Grade the student answer and save results using direct SQL queries.
        """
        session = self.get_session()
        start_time = datetime.utcnow()
        
        try:
            # Check if already graded
            existing_row = session.execute(
                text("SELECT TOP 1 * FROM grading_results WHERE student_answer_id = :sid"),
                {"sid": student_answer.id}
            ).fetchone()
            if existing_row:
                logger.info(f"Using existing grading result for student {student_answer.student_id}")
                return self._format_grading_response_raw(_row_to_ns(existing_row), session)
            
            # Prepare key concepts data for LLM
            concepts_data = []
            for concept in key_concepts:
                keywords = []
                if getattr(concept, "keywords", None):
                    try:
                        keywords = json.loads(concept.keywords)
                    except Exception:
                        keywords = []
                concepts_data.append({
                    "concept": concept.concept_name,
                    "importance": concept.importance_score,
                    "keywords": keywords,
                    "explanation": concept.concept_description,
                    "max_points": concept.max_points
                })
            
            # Use LLM to analyze semantic similarity
            semantic_analysis = await llm_service.analyze_semantic_similarity(
                question.ideal_answer,
                student_answer.answer_text,
                concepts_data
            )
            
            # Prepare rubric data (load from rubric_criteria if present)
            rc_rows = session.execute(
                text("SELECT * FROM rubric_criteria WHERE question_id = :qid"),
                {"qid": question.id}
            ).fetchall()
            if not rc_rows:
                rubric_data = {
                    "subject": question.subject,
                    "topic": question.topic,
                    "criteria": [
                        {
                            "name": c.concept_name,
                            "description": c.concept_description,
                            "max_points": c.max_points,
                            "weight": c.importance_score
                        }
                        for c in key_concepts
                    ],
                    "total_max_points": question.max_marks,
                    "passing_threshold": question.passing_threshold
                }
            else:
                rubric_data = {
                    "subject": question.subject,
                    "topic": question.topic,
                    "criteria": [
                        {
                            "name": r._mapping["criteria_name"],
                            "description": r._mapping["criteria_description"],
                            "max_points": r._mapping["max_points"],
                            "weight": r._mapping["weight"],
                        }
                        for r in rc_rows
                    ],
                    "total_max_points": question.max_marks,
                    "passing_threshold": question.passing_threshold
                }
            
            # Apply grading rubric using LLM
            grading_result_data = await llm_service.apply_grading_rubric(
                question.ideal_answer,
                student_answer.answer_text,
                rubric_data,
                semantic_analysis.get("concept_evaluations", []),
                semantic_analysis
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Calculate scores
            total_score = grading_result_data.get("total_score", 0)
            percentage = grading_result_data.get("percentage", 0)
            passed = grading_result_data.get("passed", percentage >= question.passing_threshold)
            
            # Insert grading result
            result_uuid = str(uuid.uuid4())
            insert_gr_sql = text(
                """
                INSERT INTO grading_results (
                    result_id, student_answer_id, total_score, max_possible_score, percentage, passed,
                    semantic_similarity, coherence_score, completeness_score, confidence_score,
                    detailed_feedback, strengths, weaknesses, suggestions,
                    grading_model, processing_time_ms, graded_at, graded_by, raw_llm_response, criteria_scores
                )
                OUTPUT INSERTED.id
                VALUES (
                    :result_id, :student_answer_id, :total_score, :max_possible_score, :percentage, :passed,
                    :semantic_similarity, :coherence_score, :completeness_score, :confidence_score,
                    :detailed_feedback, :strengths, :weaknesses, :suggestions,
                    :grading_model, :processing_time_ms, GETUTCDATE(), :graded_by, :raw_llm_response, :criteria_scores
                )
                """
            )
            params = {
                "result_id": result_uuid,
                "student_answer_id": student_answer.id,
                "total_score": total_score,
                "max_possible_score": question.max_marks,
                "percentage": percentage,
                "passed": passed,
                "semantic_similarity": semantic_analysis.get("overall_semantic_similarity", 0),
                "coherence_score": semantic_analysis.get("coherence_score", 0),
                "completeness_score": semantic_analysis.get("completeness_score", 0),
                "confidence_score": grading_result_data.get("confidence_score", 0.8),
                "detailed_feedback": grading_result_data.get("detailed_feedback", ""),
                "strengths": json.dumps(grading_result_data.get("strengths", [])),
                "weaknesses": json.dumps(grading_result_data.get("weaknesses", [])),
                "suggestions": json.dumps(grading_result_data.get("suggestions", [])),
                "grading_model": settings.llm_model,
                "processing_time_ms": processing_time,
                "graded_by": "RAGService",
                "raw_llm_response": json.dumps({"semantic_analysis": semantic_analysis, "grading_result": grading_result_data}),
                "criteria_scores": json.dumps(grading_result_data.get("criteria_scores", {})),
            }
            gr_row = session.execute(insert_gr_sql, params).fetchone()
            grading_result_id = gr_row[0] if gr_row else None
            
            # Create concept evaluations
            concept_evaluations_data = []
            for c in key_concepts:
                # Find matching concept evaluation from LLM response
                concept_eval_data = None
                for eval_data in semantic_analysis.get("concept_evaluations", []):
                    if eval_data.get("concept", "").lower() in c.concept_name.lower():
                        concept_eval_data = eval_data
                        break
                if not concept_eval_data:
                    concept_eval_data = {"present": False, "accuracy_score": 0.0, "explanation": "Concept not found in student answer", "evidence": None}
                points_awarded = concept_eval_data["accuracy_score"] * c.max_points
                session.execute(text(
                    """
                    INSERT INTO concept_evaluations (
                        grading_result_id, key_concept_id, present, accuracy_score, points_awarded, points_possible,
                        explanation, evidence_text, reasoning, evaluated_at
                    ) VALUES (
                        :grading_result_id, :key_concept_id, :present, :accuracy_score, :points_awarded, :points_possible,
                        :explanation, :evidence_text, :reasoning, GETUTCDATE()
                    )
                    """
                ), {
                    "grading_result_id": grading_result_id,
                    "key_concept_id": c.id,
                    "present": concept_eval_data["present"],
                    "accuracy_score": concept_eval_data["accuracy_score"],
                    "points_awarded": points_awarded,
                    "points_possible": c.max_points,
                    "explanation": concept_eval_data["explanation"],
                    "evidence_text": concept_eval_data.get("evidence"),
                    "reasoning": f"Accuracy: {concept_eval_data['accuracy_score']:.2f}, Points: {points_awarded:.1f}/{c.max_points}",
                })
                concept_evaluations_data.append({
                    "concept": c.concept_name,
                    "present": concept_eval_data["present"],
                    "points_awarded": points_awarded,
                    "points_possible": c.max_points,
                    "reason": concept_eval_data["explanation"],
                })
            session.commit()
                       
            response = {
                "Score": f"{total_score:.1f}/{question.max_marks}",
                "Justification": grading_result_data.get("detailed_feedback", ""),
                "Key_Concepts_Covered": [
                    f"{ev['concept']} ({ev['points_awarded']:.1f}/{ev['points_possible']:.1f} points) - {ev['reason']}"
                    for ev in concept_evaluations_data
                ],
                "Percentage": f"{percentage:.1f}%",
                "Passed": passed,
                "ProcessingTimeMs": processing_time,
                "ConfidenceScore": grading_result_data.get("confidence_score", 0.8),
                "GradingResultId": result_uuid,
            }
            logger.info(f"Successfully graded answer for student {student_answer.student_id}: {total_score:.1f}/{question.max_marks}")
            return response
        except Exception as e:
            session.rollback()
            logger.error(f"Error grading student answer: {e}")

            raise
        finally:
            session.close()

    def _format_grading_response_raw(self, grading_result: SimpleNamespace, session: Session) -> Dict[str, Any]:
        """Format existing grading result (raw SQL) into the required response format"""
        rows = session.execute(text(
            """
            SELECT ce.*, kc.concept_name, kc.max_points
            FROM concept_evaluations ce
            INNER JOIN key_concepts kc ON ce.key_concept_id = kc.id
            WHERE ce.grading_result_id = :gid
            ORDER BY ce.id ASC
            """
        ), {"gid": grading_result.id}).fetchall()
        key_concepts_covered = []
        for row in rows:
            m = row._mapping if hasattr(row, "_mapping") else row
            key_concepts_covered.append(
                f"{m['concept_name']} ({m['points_awarded']:.1f}/{m['points_possible']:.1f} points) - {m['explanation']}"
            )
        return {
            "Score": f"{grading_result.total_score:.1f}/{grading_result.max_possible_score}",
            "Justification": grading_result.detailed_feedback,
            "Key_Concepts_Covered": key_concepts_covered,
            "Percentage": f"{grading_result.percentage:.1f}%",
            "Passed": grading_result.passed,
            "ProcessingTimeMs": grading_result.processing_time_ms,
            "ConfidenceScore": grading_result.confidence_score,
            "GradingResultId": grading_result.result_id,
        }
