"""
Pydantic models for the AI Examiner System
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class GradingCriteria(BaseModel):
    """Individual grading criterion"""
    name: str = Field(..., description="Name of the criterion")
    description: str = Field(..., description="Description of what this criterion evaluates")
    max_points: float = Field(..., gt=0, description="Maximum points for this criterion")
    weight: float = Field(default=1.0, ge=0, le=1, description="Weight of this criterion (0-1)")


class GradingRubric(BaseModel):
    """Complete grading rubric for an answer"""
    subject: str = Field(..., description="Subject area (e.g., Physics, History)")
    topic: str = Field(..., description="Specific topic within the subject")
    criteria: List[GradingCriteria] = Field(..., min_items=1, description="List of grading criteria")
    total_max_points: float = Field(..., gt=0, description="Maximum possible total score")
    passing_threshold: float = Field(default=60.0, ge=0, le=100, description="Minimum percentage to pass")
    
    @validator('total_max_points')
    def validate_total_points(cls, v, values):
        if 'criteria' in values:
            calculated_total = sum(c.max_points for c in values['criteria'])
            if abs(v - calculated_total) > 0.01:  # Allow for small floating point differences
                raise ValueError("total_max_points must equal sum of criteria max_points")
        return v


class KeyConcept(BaseModel):
    """A key concept extracted from an ideal answer"""
    concept: str = Field(..., description="The key concept or idea")
    importance: float = Field(..., ge=0, le=1, description="Importance score (0-1)")
    keywords: List[str] = Field(default=[], description="Associated keywords")
    explanation: str = Field(..., description="Detailed explanation of the concept")


class IdealAnswer(BaseModel):
    """Model for ideal/reference answers"""
    id: Optional[str] = None
    question_id: str = Field(..., description="Associated question identifier")
    content: str = Field(..., min_length=10, description="The ideal answer content")
    key_concepts: List[KeyConcept] = Field(default=[], description="Extracted key concepts")
    rubric: GradingRubric = Field(..., description="Grading rubric for this answer")
    subject: str = Field(..., description="Academic subject")
    difficulty_level: str = Field(default="intermediate", description="Difficulty level")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class StudentAnswer(BaseModel):
    """Model for student submitted answers"""
    id: Optional[str] = None
    student_id: str = Field(..., description="Student identifier")
    question_id: str = Field(..., description="Associated question identifier")
    content: str = Field(..., min_length=1, max_length=2000, description="Student's answer")
    submitted_at: datetime = Field(default_factory=datetime.now)
    language: str = Field(default="en", description="Language of the answer")


class ConceptEvaluation(BaseModel):
    """Evaluation of a specific concept in student answer"""
    concept: str = Field(..., description="The concept being evaluated")
    present: bool = Field(..., description="Whether the concept is present in student answer")
    accuracy_score: float = Field(..., ge=0, le=1, description="Accuracy score for this concept (0-1)")
    explanation: str = Field(..., description="Detailed explanation of the evaluation")
    evidence: Optional[str] = Field(None, description="Quote from student answer supporting the evaluation")


class GradingResult(BaseModel):
    """Complete grading result for a student answer"""
    id: Optional[str] = None
    student_answer_id: str = Field(..., description="Reference to student answer")
    ideal_answer_id: str = Field(..., description="Reference to ideal answer used")
    total_score: float = Field(..., ge=0, description="Total score awarded")
    max_possible_score: float = Field(..., gt=0, description="Maximum possible score")
    percentage: float = Field(..., ge=0, le=100, description="Percentage score")
    passed: bool = Field(..., description="Whether the answer meets passing criteria")
    
    # Detailed breakdown
    concept_evaluations: List[ConceptEvaluation] = Field(..., description="Evaluation of each key concept")
    criteria_scores: Dict[str, float] = Field(..., description="Score for each grading criterion")
    
    # AI Analysis
    semantic_similarity: float = Field(..., ge=0, le=1, description="Overall semantic similarity to ideal answer")
    coherence_score: float = Field(..., ge=0, le=1, description="Coherence and structure score")
    completeness_score: float = Field(..., ge=0, le=1, description="Completeness score")
    
    # Feedback
    strengths: List[str] = Field(default=[], description="Identified strengths in the answer")
    weaknesses: List[str] = Field(default=[], description="Identified weaknesses")
    suggestions: List[str] = Field(default=[], description="Suggestions for improvement")
    detailed_feedback: str = Field(..., description="Comprehensive feedback text")
    
    # Metadata
    graded_at: datetime = Field(default_factory=datetime.now)
    grading_model: str = Field(..., description="LLM model used for grading")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the grading result")


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    GITHUB = "github"


class LLMModel(str, Enum):
    """Supported LLM models"""
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"
    GITHUB_GPT4_NANO = "openai/gpt-4.1-nano"
    GITHUB_GPT4O = "openai/gpt-4o"
    GITHUB_GPT4O_MINI = "openai/gpt-4o-mini"


class GradingRequest(BaseModel):
    """Request model for grading an answer"""
    student_answer: StudentAnswer = Field(..., description="The student answer to grade")
    ideal_answer: IdealAnswer = Field(..., description="The ideal answer to compare against")
    additional_instructions: Optional[str] = Field(None, description="Additional grading instructions")


class GradingResponse(BaseModel):
    """Response model for grading request"""
    result: GradingResult = Field(..., description="The grading result")
    processing_time_ms: float = Field(..., description="Time taken to process the request")
    success: bool = Field(..., description="Whether the grading was successful")
    error_message: Optional[str] = Field(None, description="Error message if grading failed")


class BatchGradingRequest(BaseModel):
    """Request model for batch grading"""
    requests: List[GradingRequest] = Field(..., min_items=1, max_items=50, description="List of grading requests")


class BatchGradingResponse(BaseModel):
    """Response model for batch grading"""
    results: List[GradingResponse] = Field(..., description="List of grading responses")
    total_processed: int = Field(..., description="Total number of requests processed")
    total_successful: int = Field(..., description="Number of successful gradings")
    total_failed: int = Field(..., description="Number of failed gradings")
    total_processing_time_ms: float = Field(..., description="Total processing time")


# Database Models (for SQLAlchemy)
class BaseEntity(BaseModel):
    """Base entity with common fields"""
    id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True