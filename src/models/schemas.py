"""
Pydantic models for the AI Examiner System
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator

#######################################################################




# class KeyConcept(Base):
#     """Key concepts extracted from ideal answers"""
#     __tablename__ = "key_concepts"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     question_id = Field(Integer, ForeignKey("questions.id"), nullable=False)
#     concept_name = Field(String(255), nullable=False)
#     concept_description = Field(Text, nullable=False)
#     importance_score = Field(Float, nullable=False)  # 0.0 to 1.0
#     keywords = Field(Text)  # JSON array of keywords
#     max_points = Field(Float, nullable=False)
#     extraction_method = Field(String(50), default="llm_extracted")  # llm_extracted, manual
#     created_at = Field(DateTime, default=datetime.utcnow)
    
#     # Relationships
#     question = relationship("Question", back_populates="key_concepts")
#     concept_evaluations = relationship("ConceptEvaluation", back_populates="key_concept")


# class RubricCriteria(Base):
#     """Grading rubric criteria for questions"""
#     __tablename__ = "rubric_criteria"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     question_id = Field(Integer, ForeignKey("questions.id"), nullable=False)
#     criteria_name = Field(String(255), nullable=False)
#     criteria_description = Field(Text, nullable=False)
#     max_points = Field(Float, nullable=False)
#     weight = Field(Float, default=1.0)
#     created_at = Field(DateTime, default=datetime.utcnow)
    
#     # Relationships
#     question = relationship("Question", back_populates="rubric_criteria")


# class StudentAnswer(Base):
#     """Student submitted answers"""
#     __tablename__ = "student_answers"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     answer_id = Field(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
#     student_id = Field(String(255), nullable=False, index=True)
#     question_id = Field(Integer, ForeignKey("questions.id"), nullable=False)
#     answer_text = Field(Text, nullable=False)
#     submitted_at = Field(DateTime, default=datetime.utcnow)
#     language = Field(String(10), default="en")
#     word_count = Field(Integer)
    
#     # Relationships
#     question = relationship("Question", back_populates="student_answers")
#     grading_results = relationship("GradingResult", back_populates="student_answer")


# class GradingResult(Base):
#     """AI grading results"""
#     __tablename__ = "grading_results"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     result_id = Field(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
#     student_answer_id = Field(Integer, ForeignKey("student_answers.id"), nullable=False)
    
#     # Scores
#     total_score = Field(Float, nullable=False)
#     max_possible_score = Field(Float, nullable=False)
#     percentage = Field(Float, nullable=False)
#     passed = Field(Boolean, nullable=False)
    
#     # AI Analysis Metrics
#     semantic_similarity = Field(Float, nullable=False)  # 0.0 to 1.0
#     coherence_score = Field(Float, nullable=False)
#     completeness_score = Field(Float, nullable=False)
#     confidence_score = Field(Float, nullable=False)
    
#     # Feedback
#     detailed_feedback = Field(Text, nullable=False)
#     strengths = Field(Text)  # JSON array
#     weaknesses = Field(Text)  # JSON array
#     suggestions = Field(Text)  # JSON array
    
#     # Metadata
#     grading_model = Field(String(100), nullable=False)
#     processing_time_ms = Field(Float)
#     graded_at = Field(DateTime, default=datetime.utcnow)
#     graded_by = Field(String(100), default="ai_examiner")
    
#     # Additional JSON data for complex structures
#     raw_llm_response = Field(Text)  # Store the full LLM response
#     criteria_scores = Field(Text)  # JSON of individual criteria scores
    
#     # Relationships
#     student_answer = relationship("StudentAnswer", back_populates="grading_results")
#     concept_evaluations = relationship("ConceptEvaluation", back_populates="grading_result")


# class ConceptEvaluation(Base):
#     """Evaluation of individual key concepts in student answers"""
#     __tablename__ = "concept_evaluations"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     grading_result_id = Field(Integer, ForeignKey("grading_results.id"), nullable=False)
#     key_concept_id = Field(Integer, ForeignKey("key_concepts.id"), nullable=False)
    
#     # Evaluation Results
#     present = Field(Boolean, nullable=False)
#     accuracy_score = Field(Float, nullable=False)  # 0.0 to 1.0
#     points_awarded = Field(Float, nullable=False)
#     points_possible = Field(Float, nullable=False)
    
#     # Evidence and Reasoning
#     explanation = Field(Text, nullable=False)
#     evidence_text = Field(Text)  # Quote from student answer
#     reasoning = Field(Text)  # Why this score was awarded
    
#     # Metadata
#     evaluated_at = Field(DateTime, default=datetime.utcnow)
    
#     # Relationships
#     grading_result = relationship("GradingResult", back_populates="concept_evaluations")
#     key_concept = relationship("KeyConcept", back_populates="concept_evaluations")


# class GradingSession(Base):
#     """Track grading sessions and batches"""
#     __tablename__ = "grading_sessions"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     session_id = Field(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
#     batch_name = Field(String(255))
#     total_answers = Field(Integer, default=0)
#     completed_answers = Field(Integer, default=0)
#     failed_answers = Field(Integer, default=0)
    
#     # Session Metadata
#     started_at = Field(DateTime, default=datetime.utcnow)
#     completed_at = Field(DateTime)
#     total_processing_time_ms = Field(Float)
#     average_score = Field(Float)
    
#     # Configuration used
#     llm_provider = Field(String(50))
#     llm_model = Field(String(100))
#     grading_temperature = Field(Float)
    
#     # Status
#     status = Field(String(20), default="in_progress")  # in_progress, completed, failed


# class AuditLog(Base):
#     """Audit log for all system operations"""
#     __tablename__ = "audit_logs"
    
#     id = Field(Integer, primary_key=True, autoincrement=True)
#     log_id = Field(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    
#     # Event Details
#     event_type = Field(String(100), nullable=False)  # grading, concept_extraction, etc.
#     entity_type = Field(String(100))  # question, student_answer, grading_result
#     entity_id = Field(String(255))
    
#     # Event Data
#     event_data = Field(Text)  # JSON data
#     result_status = Field(String(20))  # success, failure, warning
#     error_message = Field(Text)
    
#     # Metadata
#     user_id = Field(String(255))
#     ip_address = Field(String(45))
#     user_agent = Field(String(500))
#     created_at = Field(DateTime, default=datetime.utcnow)
#     processing_time_ms = Field(Float)


# # Database connection and session management
# class DatabaseManager:
#     """Database connection manager for MSSQL Server"""
    
#     def __init__(self, connection_string: str):
#         self.connection_string = connection_string
#         self.engine = None
#         self.SessionLocal = None
#         self.initialize_database()
    
#     def initialize_database(self):
#         """Initialize database connection and create tables"""
#         try:
#             self.engine = create_engine(
#                 self.connection_string,
#                 echo=False,  # Set to True for SQL debugging
#                 pool_pre_ping=True,
#                 pool_recycle=3600
#             )
            
#             # Create all tables
#             Base.metadata.create_all(bind=self.engine)
            
#             # Create session factory
#             self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
#             print("Database initialized successfully")
            
#         except Exception as e:
#             print(f"Failed to initialize database: {e}")
#             raise
    
#     def get_session(self):
#         """Get a database session"""
#         if not self.SessionLocal:
#             raise RuntimeError("Database not initialized")
        
#         return self.SessionLocal()
    
#     def close(self):
#         """Close database connection"""
#         if self.engine:
#             self.engine.dispose()


#######################################################################

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
    criteria: List[GradingCriteria] = Field(..., min_items=1, description="List of grading criteria") # type: ignore
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
    question_id: int = Field(..., description="Associated question identifier")
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
    student_id: int = Field(..., description="Student identifier")
    question_id: int = Field(..., description="Associated question identifier")
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
    GITHUB = "github"


class LLMModel(str, Enum):
    """Supported LLM models"""
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