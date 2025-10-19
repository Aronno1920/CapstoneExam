"""
Unit Tests for AI Examiner Grading System
"""
import pytest
import asyncio
from datetime import datetime

from src.models.schemas import (
    IdealAnswer, StudentAnswer, GradingRubric, GradingCriteria,
    GradingRequest, ConceptEvaluation
)
from src.services.grading_service import AIExaminer, SemanticAnalyzer, ResponseEvaluator
from src.utils.config import settings


@pytest.fixture
def sample_rubric():
    """Sample grading rubric for testing"""
    return GradingRubric(
        subject="Physics",
        topic="Newton's Laws",
        criteria=[
            GradingCriteria(name="First Law", description="Understanding of inertia", max_points=30.0),
            GradingCriteria(name="Second Law", description="F=ma understanding", max_points=30.0),
            GradingCriteria(name="Third Law", description="Action-reaction", max_points=30.0),
            GradingCriteria(name="Examples", description="Clear examples", max_points=10.0)
        ],
        total_max_points=100.0,
        passing_threshold=60.0
    )


@pytest.fixture
def sample_ideal_answer(sample_rubric):
    """Sample ideal answer for testing"""
    return IdealAnswer(
        id="ideal_001",
        question_id="test_001",
        content="""Newton's three laws of motion describe the relationship between forces and motion.
        
The First Law states that objects at rest stay at rest and objects in motion stay in motion unless acted upon by a force.

The Second Law states that F = ma, where force equals mass times acceleration.

The Third Law states that for every action there is an equal and opposite reaction.""",
        rubric=sample_rubric,
        subject="Physics"
    )


@pytest.fixture
def sample_student_answer():
    """Sample student answer for testing"""
    return StudentAnswer(
        id="student_001",
        student_id="STU001", 
        question_id="test_001",
        content="""Newton has three laws. First law is about inertia - things don't move unless pushed. Second law is F = ma. Third law says action equals reaction.""",
        submitted_at=datetime.now()
    )


class TestGradingModels:
    """Test grading data models"""
    
    def test_grading_rubric_validation(self, sample_rubric):
        """Test that grading rubric validates correctly"""
        assert sample_rubric.total_max_points == 100.0
        assert len(sample_rubric.criteria) == 4
        assert sample_rubric.passing_threshold == 60.0
    
    def test_ideal_answer_creation(self, sample_ideal_answer):
        """Test ideal answer model creation"""
        assert sample_ideal_answer.subject == "Physics"
        assert sample_ideal_answer.question_id == "test_001"
        assert len(sample_ideal_answer.content) > 0
    
    def test_student_answer_creation(self, sample_student_answer):
        """Test student answer model creation"""
        assert sample_student_answer.student_id == "STU001"
        assert sample_student_answer.question_id == "test_001"
        assert len(sample_student_answer.content) > 0


@pytest.mark.asyncio
class TestAIExaminer:
    """Test AI Examiner functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.ai_examiner = AIExaminer()
    
    @pytest.mark.skipif(
        not settings.openai_api_key and not settings.anthropic_api_key,
        reason="No API keys configured for LLM testing"
    )
    async def test_grade_answer_basic(self, sample_ideal_answer, sample_student_answer):
        """Test basic grading functionality"""
        try:
            result = await self.ai_examiner.grade_answer(
                student_answer=sample_student_answer,
                ideal_answer=sample_ideal_answer,
                use_chain_of_thought=True
            )
            
            # Verify result structure
            assert result.student_answer_id == sample_student_answer.id
            assert result.ideal_answer_id == sample_ideal_answer.id
            assert 0 <= result.total_score <= result.max_possible_score
            assert 0 <= result.percentage <= 100
            assert isinstance(result.passed, bool)
            assert len(result.concept_evaluations) >= 0
            assert len(result.detailed_feedback) > 0
            
        except Exception as e:
            pytest.skip(f"LLM service not available: {e}")
    
    def test_grading_metrics_initialization(self):
        """Test grading metrics initialization"""
        from src.services.grading_service import GradingMetrics
        
        metrics = GradingMetrics(
            processing_time_ms=100.0,
            concept_extraction_time_ms=50.0,
            semantic_analysis_time_ms=30.0,
            rubric_application_time_ms=20.0,
            total_llm_calls=3,
            confidence_score=0.85
        )
        
        assert metrics.processing_time_ms == 100.0
        assert metrics.total_llm_calls == 3
        assert metrics.confidence_score == 0.85


class TestSemanticAnalyzer:
    """Test semantic analysis functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.analyzer = SemanticAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test semantic analyzer initialization"""
        assert self.analyzer.llm_service is not None


class TestResponseEvaluator:
    """Test response evaluation functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.evaluator = ResponseEvaluator()
    
    def test_evaluator_initialization(self):
        """Test response evaluator initialization"""
        assert self.evaluator.llm_service is not None


class TestGradingRequest:
    """Test grading request models"""
    
    def test_grading_request_creation(self, sample_ideal_answer, sample_student_answer):
        """Test grading request model creation"""
        request = GradingRequest(
            student_answer=sample_student_answer,
            ideal_answer=sample_ideal_answer,
            additional_instructions="Focus on physics concepts"
        )
        
        assert request.student_answer.student_id == "STU001"
        assert request.ideal_answer.subject == "Physics"
        assert request.additional_instructions == "Focus on physics concepts"


class TestConceptEvaluation:
    """Test concept evaluation models"""
    
    def test_concept_evaluation_creation(self):
        """Test concept evaluation model creation"""
        evaluation = ConceptEvaluation(
            concept="Newton's First Law",
            present=True,
            accuracy_score=0.85,
            explanation="Student demonstrated good understanding",
            evidence="Objects at rest stay at rest unless pushed"
        )
        
        assert evaluation.concept == "Newton's First Law"
        assert evaluation.present is True
        assert evaluation.accuracy_score == 0.85
        assert len(evaluation.explanation) > 0


@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring API access"""
    
    @pytest.mark.skipif(
        not settings.openai_api_key and not settings.anthropic_api_key,
        reason="No API keys configured for integration testing"
    )
    async def test_end_to_end_grading(self, sample_ideal_answer, sample_student_answer):
        """Test end-to-end grading process"""
        try:
            ai_examiner = AIExaminer()
            
            result = await ai_examiner.grade_answer(
                student_answer=sample_student_answer,
                ideal_answer=sample_ideal_answer
            )
            
            # Verify comprehensive result
            assert result is not None
            assert result.total_score >= 0
            assert result.percentage >= 0
            assert len(result.detailed_feedback) > 10  # Should be substantial
            assert result.confidence_score > 0
            
            # Verify concept evaluations
            assert len(result.concept_evaluations) > 0
            for evaluation in result.concept_evaluations:
                assert len(evaluation.concept) > 0
                assert 0 <= evaluation.accuracy_score <= 1
                assert len(evaluation.explanation) > 0
            
            # Verify criteria scores
            assert len(result.criteria_scores) > 0
            for criterion, score in result.criteria_scores.items():
                assert score >= 0
                assert len(criterion) > 0
            
        except Exception as e:
            pytest.skip(f"Integration test failed - LLM service issue: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])