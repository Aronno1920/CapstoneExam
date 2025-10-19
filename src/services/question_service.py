"""
Question Service for MSSQL Server Operations
Handles the specific workflow: retrieve ideal answer -> extract concepts -> retrieve student answer -> grade and save
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models.question import (
    Question, KeyConcept, RubricCriteria, StudentAnswer, 
    GradingResult, ConceptEvaluation, GradingSession, AuditLog,
    DatabaseManager
)
from ..utils.config import settings
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)


class QuestionService:
    """Question service implementing the required workflow"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    def log_audit_event(self, session: Session, event_type: str, entity_type: str, 
                       entity_id: str, event_data: Dict[str, Any], 
                       result_status: str = "success", error_message: str = None):
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
    
    # Step 1: Retrieve Ideal Answer and Marks
    def get_question_with_ideal_answer(self, question_id: str) -> Optional[Question]:
        """
        Step 1: Retrieve ideal answer and marks for a question
        
        Args:
            question_id: Unique identifier for the question
            
        Returns:
            Question object with ideal answer and marks, or None if not found
        """
        session = self.get_session()
        try:
            question = session.query(Question).filter(
                Question.question_id == question_id
            ).first()
            
            if question:
                logger.info(f"Retrieved question {question_id}")
                
                # Log audit event
                self.log_audit_event(
                    session, "question_retrieval", "question", question_id,
                    {"max_marks": question.max_marks, "subject": question.subject}
                )
            
            return question
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving question {question_id}: {e}")
            self.log_audit_event(
                session, "question_retrieval", "question", question_id,
                {}, "failure", str(e)
            )
            return None
        finally:
            session.close()
    
    def get_question_details(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Get question details with key concepts count (for API responses)
        
        Args:
            question_id: Unique identifier for the question
            
        Returns:
            Dictionary with question details and key concepts count, or None if not found
        """
        session = self.get_session()
        try:
            question = session.query(Question).filter(
                Question.question_id == question_id
            ).first()
            
            if not question:
                return None
            
            # Count key concepts while session is active
            key_concepts_count = session.query(KeyConcept).filter(
                KeyConcept.question_id == question.id
            ).count()
            
            # Build response dict while session is active
            result = {
                "id": question.id,
                "question_id": question.question_id,
                "subject": question.subject,
                "topic": question.topic,
                "question_text": question.question_text,
                "ideal_answer": question.ideal_answer,
                "max_marks": question.max_marks,
                "passing_threshold": question.passing_threshold,
                "difficulty_level": question.difficulty_level,
                "key_concepts_count": key_concepts_count
            }
            
            logger.info(f"Retrieved question {question_id} with {key_concepts_count} key concepts")
            
            # Log audit event
            self.log_audit_event(
                session, "question_retrieval", "question", question_id,
                {"max_marks": question.max_marks, "subject": question.subject}
            )
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving question {question_id}: {e}")
            self.log_audit_event(
                session, "question_retrieval", "question", question_id,
                {}, "failure", str(e)
            )
            return None
        finally:
            session.close()
    
    # Step 2: Save Semantic Understanding (Key Concepts)
    async def extract_and_save_key_concepts(self, question: Question) -> List[KeyConcept]:
        """
        Step 2: Extract key concepts from ideal answer and save to database
        
        Args:
            question: Question object with ideal answer
            
        Returns:
            List of extracted and saved KeyConcept objects
        """
        session = self.get_session()
        try:
            # Check if concepts already exist
            existing_concepts = session.query(KeyConcept).filter(
                KeyConcept.question_id == question.id
            ).all()
            
            if existing_concepts:
                logger.info(f"Using existing {len(existing_concepts)} key concepts for question {question.question_id}")
                return existing_concepts
            
            # Extract key concepts using LLM
            logger.info(f"Extracting key concepts for question {question.question_id}")
            
            concepts_data = await llm_service.extract_key_concepts(
                question.ideal_answer,
                question.subject,
                question.topic
            )
            
            # Calculate points per concept (distribute total marks)
            points_per_concept = question.max_marks / len(concepts_data) if concepts_data else 0
            
            # Save concepts to database
            saved_concepts = []
            for i, concept_data in enumerate(concepts_data):
                key_concept = KeyConcept(
                    question_id=question.id,
                    concept_name=concept_data["concept"],
                    concept_description=concept_data["explanation"],
                    importance_score=concept_data["importance"],
                    keywords=json.dumps(concept_data.get("keywords", [])),
                    max_points=points_per_concept,
                    extraction_method="llm_extracted"
                )
                session.add(key_concept)
                saved_concepts.append(key_concept)
            
            session.commit()
            
            logger.info(f"Saved {len(saved_concepts)} key concepts for question {question.question_id}")
            
            # Log audit event
            self.log_audit_event(
                session, "concept_extraction", "question", question.question_id,
                {
                    "concepts_count": len(saved_concepts),
                    "extraction_method": "llm_extracted",
                    "points_per_concept": points_per_concept
                }
            )
            
            return saved_concepts
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error extracting/saving key concepts for question {question.question_id}: {e}")
            
            self.log_audit_event(
                session, "concept_extraction", "question", question.question_id,
                {}, "failure", str(e)
            )
            raise
        finally:
            session.close()
    
    # Step 3: Retrieve Student's Submitted Answer
    def get_student_answer(self, student_id: str, question_id: str) -> Optional[StudentAnswer]:
        """
        Step 3: Retrieve student's submitted answer
        
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
    
    # Step 4: Grade and Save Results
    async def grade_and_save_result(
        self, 
        question: Question, 
        student_answer: StudentAnswer, 
        key_concepts: List[KeyConcept]
    ) -> Dict[str, Any]:
        """
        Step 4: Grade the student answer and save results in the required format
        
        Args:
            question: Question with ideal answer
            student_answer: Student's submitted answer
            key_concepts: List of key concepts for the question
            
        Returns:
            Dictionary with Score, Justification, and Key_Concepts_Covered
        """
        session = self.get_session()
        start_time = datetime.utcnow()
        
        try:
            # Check if already graded
            existing_result = session.query(GradingResult).filter(
                GradingResult.student_answer_id == student_answer.id
            ).first()
            
            if existing_result:
                logger.info(f"Using existing grading result for student {student_answer.student_id}")
                return self._format_grading_response(existing_result, session)
            
            # Prepare key concepts data for LLM
            concepts_data = []
            for concept in key_concepts:
                concepts_data.append({
                    "concept": concept.concept_name,
                    "importance": concept.importance_score,
                    "keywords": json.loads(concept.keywords) if concept.keywords else [],
                    "explanation": concept.concept_description,
                    "max_points": concept.max_points
                })
            
            # Use LLM to analyze semantic similarity
            semantic_analysis = await llm_service.analyze_semantic_similarity(
                question.ideal_answer,
                student_answer.answer_text,
                concepts_data
            )
            
            # Prepare rubric data
            rubric_criteria = session.query(RubricCriteria).filter(
                RubricCriteria.question_id == question.id
            ).all()
            
            if not rubric_criteria:
                # Create default rubric based on key concepts
                rubric_data = {
                    "subject": question.subject,
                    "topic": question.topic,
                    "criteria": [
                        {
                            "name": concept.concept_name,
                            "description": concept.concept_description,
                            "max_points": concept.max_points,
                            "weight": concept.importance_score
                        }
                        for concept in key_concepts
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
                            "name": criteria.criteria_name,
                            "description": criteria.criteria_description,
                            "max_points": criteria.max_points,
                            "weight": criteria.weight
                        }
                        for criteria in rubric_criteria
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
            
            # Create grading result record
            grading_result = GradingResult(
                student_answer_id=student_answer.id,
                total_score=total_score,
                max_possible_score=question.max_marks,
                percentage=percentage,
                passed=passed,
                semantic_similarity=semantic_analysis.get("overall_semantic_similarity", 0),
                coherence_score=semantic_analysis.get("coherence_score", 0),
                completeness_score=semantic_analysis.get("completeness_score", 0),
                confidence_score=grading_result_data.get("confidence_score", 0.8),
                detailed_feedback=grading_result_data.get("detailed_feedback", ""),
                strengths=json.dumps(grading_result_data.get("strengths", [])),
                weaknesses=json.dumps(grading_result_data.get("weaknesses", [])),
                suggestions=json.dumps(grading_result_data.get("suggestions", [])),
                grading_model=settings.llm_model,
                processing_time_ms=processing_time,
                raw_llm_response=json.dumps({
                    "semantic_analysis": semantic_analysis,
                    "grading_result": grading_result_data
                }),
                criteria_scores=json.dumps(grading_result_data.get("criteria_scores", {}))
            )
            
            session.add(grading_result)
            session.flush()  # Get the ID
            
            # Create concept evaluations
            concept_evaluations_data = []
            for i, concept in enumerate(key_concepts):
                # Find matching concept evaluation from LLM response
                concept_eval_data = None
                for eval_data in semantic_analysis.get("concept_evaluations", []):
                    if eval_data.get("concept", "").lower() in concept.concept_name.lower():
                        concept_eval_data = eval_data
                        break
                
                if not concept_eval_data:
                    # Create default evaluation
                    concept_eval_data = {
                        "present": False,
                        "accuracy_score": 0.0,
                        "explanation": "Concept not found in student answer",
                        "evidence": None
                    }
                
                points_awarded = concept_eval_data["accuracy_score"] * concept.max_points
                
                concept_evaluation = ConceptEvaluation(
                    grading_result_id=grading_result.id,
                    key_concept_id=concept.id,
                    present=concept_eval_data["present"],
                    accuracy_score=concept_eval_data["accuracy_score"],
                    points_awarded=points_awarded,
                    points_possible=concept.max_points,
                    explanation=concept_eval_data["explanation"],
                    evidence_text=concept_eval_data.get("evidence"),
                    reasoning=f"Accuracy: {concept_eval_data['accuracy_score']:.2f}, Points: {points_awarded:.1f}/{concept.max_points}"
                )
                
                session.add(concept_evaluation)
                
                # Add to response data
                concept_evaluations_data.append({
                    "concept": concept.concept_name,
                    "present": concept_eval_data["present"],
                    "points_awarded": points_awarded,
                    "points_possible": concept.max_points,
                    "reason": concept_eval_data["explanation"]
                })
            
            session.commit()
            
            # Log successful grading
            self.log_audit_event(
                session, "grading_completed", "grading_result", str(grading_result.id),
                {
                    "student_id": student_answer.student_id,
                    "question_id": question.question_id,
                    "total_score": total_score,
                    "percentage": percentage,
                    "passed": passed,
                    "processing_time_ms": processing_time
                }
            )
            
            # Format response as requested
            response = {
                "Score": f"{total_score:.1f}/{question.max_marks}",
                "Justification": grading_result_data.get("detailed_feedback", ""),
                "Key_Concepts_Covered": [
                    f"{eval_data['concept']} ({eval_data['points_awarded']:.1f}/{eval_data['points_possible']:.1f} points) - {eval_data['reason']}"
                    for eval_data in concept_evaluations_data
                ],
                "Percentage": f"{percentage:.1f}%",
                "Passed": passed,
                "ProcessingTimeMs": processing_time,
                "ConfidenceScore": grading_result_data.get("confidence_score", 0.8),
                "GradingResultId": grading_result.result_id
            }
            
            logger.info(f"Successfully graded answer for student {student_answer.student_id}: {total_score:.1f}/{question.max_marks}")
            
            return response
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error grading student answer: {e}")
            
            # Log error
            self.log_audit_event(
                session, "grading_failed", "student_answer", str(student_answer.id),
                {
                    "student_id": student_answer.student_id,
                    "question_id": question.question_id,
                    "error": str(e)
                },
                "failure", str(e)
            )
            
            raise
        finally:
            session.close()
    
    def _format_grading_response(self, grading_result: GradingResult, session: Session) -> Dict[str, Any]:
        """Format existing grading result into the required response format"""
        from sqlalchemy.orm import joinedload
        
        # Get concept evaluations with eager loading of key_concept
        concept_evaluations = session.query(ConceptEvaluation).options(
            joinedload(ConceptEvaluation.key_concept)
        ).filter(
            ConceptEvaluation.grading_result_id == grading_result.id
        ).all()
        
        key_concepts_covered = []
        for eval in concept_evaluations:
            key_concepts_covered.append(
                f"{eval.key_concept.concept_name} ({eval.points_awarded:.1f}/{eval.points_possible:.1f} points) - {eval.explanation}"
            )
        
        return {
            "Score": f"{grading_result.total_score:.1f}/{grading_result.max_possible_score}",
            "Justification": grading_result.detailed_feedback,
            "Key_Concepts_Covered": key_concepts_covered,
            "Percentage": f"{grading_result.percentage:.1f}%",
            "Passed": grading_result.passed,
            "ProcessingTimeMs": grading_result.processing_time_ms,
            "ConfidenceScore": grading_result.confidence_score,
            "GradingResultId": grading_result.result_id
        }
    
    # Complete Workflow Method
    async def complete_grading_workflow(self, question_id: str, student_id: str) -> Dict[str, Any]:
        """
        Complete grading workflow as specified:
        1. Retrieve ideal answer and marks
        2. Extract and save key concepts (semantic understanding)
        3. Retrieve student's submitted answer
        4. Grade and save results
        
        Args:
            question_id: Question identifier
            student_id: Student identifier
            
        Returns:
            Grading result in required format
        """
        logger.info(f"Starting complete grading workflow for student {student_id}, question {question_id}")
        
        # Step 1: Retrieve ideal answer and marks
        question = self.get_question_with_ideal_answer(question_id)
        if not question:
            raise ValueError(f"Question {question_id} not found")
        
        # Step 2: Extract and save key concepts (semantic understanding)
        key_concepts = await self.extract_and_save_key_concepts(question)
        if not key_concepts:
            raise ValueError(f"Failed to extract key concepts for question {question_id}")
        
        # Step 3: Retrieve student's submitted answer
        student_answer = self.get_student_answer(student_id, question_id)
        if not student_answer:
            raise ValueError(f"Student answer not found for student {student_id}, question {question_id}")
        
        # Step 4: Grade and save results
        result = await self.grade_and_save_result(question, student_answer, key_concepts)
        
        logger.info(f"Completed grading workflow for student {student_id}: {result['Score']}")
        return result
    
    # Utility Methods for Data Management
    def create_question(self, question_id: str, subject: str, topic: str, 
                       question_text: str, ideal_answer: str, max_marks: float,
                       passing_threshold: float = 60.0, difficulty_level: str = "intermediate") -> Question:
        """Create a new question with ideal answer"""
        session = self.get_session()
        try:
            question = Question(
                question_id=question_id,
                subject=subject,
                topic=topic,
                question_text=question_text,
                ideal_answer=ideal_answer,
                max_marks=max_marks,
                passing_threshold=passing_threshold,
                difficulty_level=difficulty_level
            )
            session.add(question)
            session.commit()
            session.refresh(question)
            
            logger.info(f"Created question {question_id}")
            return question
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating question {question_id}: {e}")
            raise
        finally:
            session.close()
    
    def create_student_answer(self, student_id: str, question_id: str, 
                            answer_text: str, language: str = "en") -> StudentAnswer:
        """Create a new student answer"""
        session = self.get_session()
        try:
            # Get question
            # question = session.query(Question).filter(
            #     Question.question_id == question_id
            # ).first()
            
            
            question = session.query(Question).options(
                joinedload(Question.key_concepts)
            ).filter(
                Question.question_id == question_id
            ).first()
            
            
            
            if not question:
                raise ValueError(f"Question {question_id} not found")
            
            student_answer = StudentAnswer(
                student_id=student_id,
                question_id=question.id,
                answer_text=answer_text,
                language=language,
                word_count=len(answer_text.split())
            )
            session.add(student_answer)
            session.commit()
            session.refresh(student_answer)
            
            logger.info(f"Created student answer for {student_id}, question {question_id}")
            return student_answer
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating student answer: {e}")
            raise
        finally:
            session.close()
    
    def get_grading_results_by_student(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all grading results for a student"""
        session = self.get_session()
        try:
            results = session.query(GradingResult).join(StudentAnswer).filter(
                StudentAnswer.student_id == student_id
            ).all()
            
            formatted_results = []
            for result in results:
                formatted_results.append(self._format_grading_response(result, session))
            
            return formatted_results
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving grading results for student {student_id}: {e}")
            return []
        finally:
            session.close()


# Initialize question service (will be set up in main application)
question_service: QuestionService = None
