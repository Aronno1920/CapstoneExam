"""
Core Grading Service for AI Examiner System
Orchestrates the entire grading process using LLM services
"""
import json
import uuid
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from types import SimpleNamespace
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..utils.database_manager import DatabaseManager


from ..models.schemas import (
    IdealAnswer, StudentAnswer, GradingResult, ConceptEvaluation,
    KeyConcept, GradingResponse, BatchGradingRequest, BatchGradingResponse
)
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

@dataclass
class GradingMetrics:
    """Metrics collected during grading process"""
    processing_time_ms: float
    concept_extraction_time_ms: float
    semantic_analysis_time_ms: float
    rubric_application_time_ms: float
    total_llm_calls: int
    confidence_score: float


class GradingError(Exception):
    """Base exception for grading-related errors"""
    pass


class SemanticAnalyzer:
    """Handles semantic analysis of student answers against ideal answers"""
    
    def __init__(self):
        self.llm_service = llm_service
        
        
        
    
    async def extract_key_concepts(self, ideal_answer: IdealAnswer) -> List[KeyConcept]:
        """Extract key concepts from an ideal answer"""
        try:
            start_time = time.time()
            
            concepts_data = await self.llm_service.extract_key_concepts(
                ideal_answer.content,
                ideal_answer.subject,
                ideal_answer.rubric.topic
            )
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Key concept extraction completed in {processing_time:.2f}ms")
            
            # Convert to KeyConcept objects
            key_concepts = []
            for concept_data in concepts_data:
                key_concept = KeyConcept(
                    concept=concept_data["concept"],
                    importance=concept_data["importance"],
                    keywords=concept_data.get("keywords", []),
                    explanation=concept_data["explanation"]
                )
                key_concepts.append(key_concept)
            
            return key_concepts
            
        except Exception as e:
            logger.error(f"Failed to extract key concepts: {e}")
            raise GradingError(f"Key concept extraction failed: {e}")
    
    async def analyze_semantic_similarity(
        self,
        ideal_answer: IdealAnswer,
        student_answer: StudentAnswer,
        key_concepts: List[KeyConcept]
    ) -> Dict[str, Any]:
        """Analyze semantic similarity between answers"""
        try:
            start_time = time.time()
            
            # Convert key concepts to dict format for LLM
            concepts_data = [
                {
                    "concept": kc.concept,
                    "importance": kc.importance,
                    "keywords": kc.keywords,
                    "explanation": kc.explanation
                }
                for kc in key_concepts
            ]
            
            analysis_result = await self.llm_service.analyze_semantic_similarity(
                ideal_answer.content,
                student_answer.content,
                concepts_data
            )
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Semantic analysis completed in {processing_time:.2f}ms")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Semantic similarity analysis failed: {e}")
            raise GradingError(f"Semantic analysis failed: {e}")


class ResponseEvaluator:
    """Evaluates student responses against grading rubrics"""
    
    def __init__(self):
        self.llm_service = llm_service
    
    async def apply_rubric(
        self,
        ideal_answer: IdealAnswer,
        student_answer: StudentAnswer,
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply grading rubric to generate scores and feedback"""
        try:
            start_time = time.time()
            
            # Convert rubric to dict format
            rubric_data = {
                "subject": ideal_answer.rubric.subject,
                "topic": ideal_answer.rubric.topic,
                "criteria": [
                    {
                        "name": criterion.name,
                        "description": criterion.description,
                        "max_points": criterion.max_points,
                        "weight": criterion.weight
                    }
                    for criterion in ideal_answer.rubric.criteria
                ],
                "total_max_points": ideal_answer.rubric.total_max_points,
                "passing_threshold": ideal_answer.rubric.passing_threshold
            }
            
            rubric_result = await self.llm_service.apply_grading_rubric(
                ideal_answer.content,
                student_answer.content,
                rubric_data,
                semantic_analysis.get("concept_evaluations", []),
                semantic_analysis
            )
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Rubric application completed in {processing_time:.2f}ms")
            
            return rubric_result
            
        except Exception as e:
            logger.error(f"Rubric application failed: {e}")
            raise GradingError(f"Rubric application failed: {e}")
    
    async def chain_of_thought_grading(
        self,
        ideal_answer: IdealAnswer,
        student_answer: StudentAnswer
    ) -> Dict[str, Any]:
        """Perform comprehensive Chain-of-Thought grading"""
        try:
            start_time = time.time()
            
            # Convert rubric to dict format
            rubric_data = {
                "subject": ideal_answer.rubric.subject,
                "topic": ideal_answer.rubric.topic,
                "criteria": [
                    {
                        "name": criterion.name,
                        "description": criterion.description,
                        "max_points": criterion.max_points,
                        "weight": criterion.weight
                    }
                    for criterion in ideal_answer.rubric.criteria
                ],
                "total_max_points": ideal_answer.rubric.total_max_points,
                "passing_threshold": ideal_answer.rubric.passing_threshold
            }
            
            cot_result = await self.llm_service.chain_of_thought_grading(
                ideal_answer.content,
                student_answer.content,
                ideal_answer.subject,
                rubric_data
            )
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Chain-of-thought grading completed in {processing_time:.2f}ms")
            
            return cot_result
            
        except Exception as e:
            logger.error(f"Chain-of-thought grading failed: {e}")
            raise GradingError(f"Chain-of-thought grading failed: {e}")


class GradeService:
    """Main AI Examiner class that orchestrates the entire grading process"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.semantic_analyzer = SemanticAnalyzer()
        self.response_evaluator = ResponseEvaluator()
        self.llm_service = llm_service
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    async def grade_answer(
        self,
        student_answer: StudentAnswer,
        ideal_answer: IdealAnswer,
        use_chain_of_thought: bool = True
    ) -> GradingResult:
        """
        Grade a student answer against an ideal answer
        
        Args:
            student_answer: The student's submitted answer
            ideal_answer: The ideal/reference answer with rubric
            use_chain_of_thought: Whether to use Chain-of-Thought grading (recommended)
        
        Returns:
            Complete grading result with scores and feedback
        """
        start_time = time.time()
        metrics = GradingMetrics(0, 0, 0, 0, 0, 0.0)
        
        try:
            logger.info(f"Starting grading process for student {student_answer.student_id}")
            
            if use_chain_of_thought:
                # Use comprehensive Chain-of-Thought grading (recommended approach)
                result = await self._grade_with_chain_of_thought(
                    student_answer, ideal_answer, metrics
                )
            else:
                # Use step-by-step grading (alternative approach)
                result = await self._grade_step_by_step(
                    student_answer, ideal_answer, metrics
                )
            
            # Calculate total processing time
            total_time = (time.time() - start_time) * 1000
            metrics.processing_time_ms = total_time
            
            logger.info(f"Grading completed in {total_time:.2f}ms with {metrics.total_llm_calls} LLM calls")
            
            return result
            
        except Exception as e:
            logger.error(f"Grading failed: {e}")
            raise GradingError(f"Failed to grade answer: {e}")
    
    async def _grade_with_chain_of_thought(
        self,
        student_answer: StudentAnswer,
        ideal_answer: IdealAnswer,
        metrics: GradingMetrics
    ) -> GradingResult:
        """Grade using Chain-of-Thought approach (recommended)"""
        
        # Perform comprehensive Chain-of-Thought grading
        start_time = time.time()
        cot_result = await self.response_evaluator.chain_of_thought_grading(
            ideal_answer, student_answer
        )
        metrics.total_llm_calls += 1
        cot_time = (time.time() - start_time) * 1000
        
        # Extract results from Chain-of-Thought response
        final_result = cot_result.get("step5_final_result", {})
        concept_comparisons = cot_result.get("step3_concept_comparison", [])
        rubric_scores = cot_result.get("step4_rubric_scores", {})
        
        # Convert concept comparisons to ConceptEvaluation objects
        concept_evaluations = []
        for comp in concept_comparisons:
            concept_eval = ConceptEvaluation(
                concept=comp.get("concept", ""),
                present=comp.get("present", False),
                accuracy_score=comp.get("accuracy_percentage", 0) / 100.0,  # Convert percentage to 0-1 scale
                explanation=comp.get("evaluation", ""),
                evidence=comp.get("evidence", None)
            )
            concept_evaluations.append(concept_eval)
        
        # Extract criteria scores
        criteria_scores = {}
        for criterion_name, criterion_data in rubric_scores.items():
            if isinstance(criterion_data, dict):
                criteria_scores[criterion_name] = criterion_data.get("points_awarded", 0)
            else:
                criteria_scores[criterion_name] = criterion_data
        
        # Calculate percentage and pass status
        total_score = final_result.get("total_score", 0)
        max_possible = final_result.get("max_possible", ideal_answer.rubric.total_max_points)
        percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
        passed = percentage >= ideal_answer.rubric.passing_threshold
        
        # Create grading result
        grading_result = GradingResult(
            id=str(uuid.uuid4()),
            student_answer_id=student_answer.id or str(uuid.uuid4()),
            ideal_answer_id=ideal_answer.id or str(uuid.uuid4()),
            total_score=total_score,
            max_possible_score=max_possible,
            percentage=percentage,
            passed=passed,
            
            # Detailed breakdown
            concept_evaluations=concept_evaluations,
            criteria_scores=criteria_scores,
            
            # AI Analysis scores (estimated from CoT result)
            semantic_similarity=self._extract_similarity_score(cot_result),
            coherence_score=cot_result.get("step2_student_analysis", {}).get("overall_coherence", 0.8),
            completeness_score=self._calculate_completeness_score(concept_evaluations),
            
            # Feedback
            strengths=final_result.get("strengths", []),
            weaknesses=final_result.get("areas_for_improvement", []),
            suggestions=final_result.get("specific_suggestions", []),
            detailed_feedback=final_result.get("overall_feedback", ""),
            
            # Metadata
            graded_at=datetime.now(),
            grading_model=settings.llm_model,
            confidence_score=final_result.get("confidence_level", 0.85)
        )
        
        return grading_result
    
    async def _grade_step_by_step(
        self,
        student_answer: StudentAnswer,
        ideal_answer: IdealAnswer,
        metrics: GradingMetrics
    ) -> GradingResult:
        """Grade using step-by-step approach (alternative)"""
        
        # Step 1: Extract key concepts if not already present
        key_concepts = ideal_answer.key_concepts
        if not key_concepts:
            start_time = time.time()
            key_concepts = await self.semantic_analyzer.extract_key_concepts(ideal_answer)
            metrics.concept_extraction_time_ms = (time.time() - start_time) * 1000
            metrics.total_llm_calls += 1
        
        # Step 2: Analyze semantic similarity
        start_time = time.time()
        semantic_analysis = await self.semantic_analyzer.analyze_semantic_similarity(
            ideal_answer, student_answer, key_concepts
        )
        metrics.semantic_analysis_time_ms = (time.time() - start_time) * 1000
        metrics.total_llm_calls += 1
        
        # Step 3: Apply grading rubric
        start_time = time.time()
        rubric_result = await self.response_evaluator.apply_rubric(
            ideal_answer, student_answer, semantic_analysis
        )
        metrics.rubric_application_time_ms = (time.time() - start_time) * 1000
        metrics.total_llm_calls += 1
        
        # Step 4: Construct final result
        concept_evaluations = []
        for eval_data in semantic_analysis.get("concept_evaluations", []):
            concept_eval = ConceptEvaluation(
                concept=eval_data["concept"],
                present=eval_data["present"],
                accuracy_score=eval_data["accuracy_score"],
                explanation=eval_data["explanation"],
                evidence=eval_data.get("evidence", None)
            )
            concept_evaluations.append(concept_eval)
        
        # Calculate final scores
        total_score = rubric_result.get("total_score", 0)
        max_possible = ideal_answer.rubric.total_max_points
        percentage = rubric_result.get("percentage", 0)
        passed = rubric_result.get("passed", percentage >= ideal_answer.rubric.passing_threshold)
        
        # Create grading result
        grading_result = GradingResult(
            id=str(uuid.uuid4()),
            student_answer_id=student_answer.id or str(uuid.uuid4()),
            ideal_answer_id=ideal_answer.id or str(uuid.uuid4()),
            total_score=total_score,
            max_possible_score=max_possible,
            percentage=percentage,
            passed=passed,
            
            # Detailed breakdown
            concept_evaluations=concept_evaluations,
            criteria_scores=rubric_result.get("criteria_scores", {}),
            
            # AI Analysis
            semantic_similarity=semantic_analysis.get("overall_semantic_similarity", 0),
            coherence_score=semantic_analysis.get("coherence_score", 0),
            completeness_score=semantic_analysis.get("completeness_score", 0),
            
            # Feedback
            strengths=rubric_result.get("strengths", []),
            weaknesses=rubric_result.get("weaknesses", []),
            suggestions=rubric_result.get("suggestions", []),
            detailed_feedback=rubric_result.get("detailed_feedback", ""),
            
            # Metadata
            graded_at=datetime.now(),
            grading_model=settings.llm_model,
            confidence_score=rubric_result.get("confidence_score", 0.85)
        )
        
        return grading_result
    
    def _extract_similarity_score(self, cot_result: Dict[str, Any]) -> float:
        """Extract semantic similarity score from Chain-of-Thought result"""
        concept_comparisons = cot_result.get("step3_concept_comparison", [])
        if not concept_comparisons:
            return 0.8  # Default estimate
        
        # Calculate weighted average based on concept accuracy
        total_weight = 0
        weighted_sum = 0
        
        for comp in concept_comparisons:
            accuracy = comp.get("accuracy_percentage", 0) / 100.0
            # Assume all concepts have equal weight for simplicity
            weight = 1.0
            weighted_sum += accuracy * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.8
    
    def _calculate_completeness_score(self, concept_evaluations: List[ConceptEvaluation]) -> float:
        """Calculate completeness score based on concept coverage"""
        if not concept_evaluations:
            return 0.7  # Default estimate
        
        present_count = sum(1 for ce in concept_evaluations if ce.present)
        return present_count / len(concept_evaluations)
    
    async def batch_grade(self, request: BatchGradingRequest) -> BatchGradingResponse:
        """Grade multiple answers in batch"""
        start_time = time.time()
        results = []
        successful = 0
        failed = 0
        
        for grading_request in request.requests:
            try:
                request_start = time.time()
                
                result = await self.grade_answer(
                    grading_request.student_answer,
                    grading_request.ideal_answer
                )
                
                processing_time = (time.time() - request_start) * 1000
                
                response = GradingResponse(
                    result=result,
                    processing_time_ms=processing_time,
                    success=True,
                    error_message=None
                )
                results.append(response)
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to grade individual request: {e}")
                
                # Create error response
                error_response = GradingResponse(
                    result=None,  # This will need to be handled properly in the API # type: ignore
                    processing_time_ms=0,
                    success=False,
                    error_message=str(e)
                )
                results.append(error_response)
                failed += 1
        
        total_time = (time.time() - start_time) * 1000
        
        return BatchGradingResponse(
            results=results,
            total_processed=len(request.requests),
            total_successful=successful,
            total_failed=failed,
            total_processing_time_ms=total_time
        )



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
        from .rag_service import RAGService
        
        logger.info(f"Starting complete grading workflow for student {student_id}, question {question_id}")
        
        # Initialize RAG service
        rag_service = RAGService(self.db_manager)
        
        # Step 1: Retrieve ideal answer and marks
        question = rag_service.get_question_with_ideal_answer(question_id)
        if not question:
            raise ValueError(f"Question {question_id} not found")
        
        # Step 2: Extract and save key concepts (semantic understanding)
        key_concepts = await rag_service.extract_and_save_key_concepts(question)
        if not key_concepts:
            raise ValueError(f"Failed to extract key concepts for question {question_id}")
        
        # Step 3: Retrieve student's submitted answer
        student_answer = rag_service.get_student_answer(student_id, question_id)
        if not student_answer:
            raise ValueError(f"Student answer not found for student {student_id}, question {question_id}")
        
        # Step 4: Grade and save results
        result = await rag_service.grade_and_save_result(question, student_answer, key_concepts)
        
        logger.info(f"Completed grading workflow for student {student_id}: {result['Score']}")
        return result







# # Global AI Examiner instance
# gradeService = GradeService()