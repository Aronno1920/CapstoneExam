"""
SQLAlchemy Database Models for MSSQL Server Integration
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import uuid

Base = declarative_base()


class Question(Base):
    """Question table - stores questions and their ideal answers"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String(255), unique=True, nullable=False, index=True)
    subject = Column(String(100), nullable=False)
    topic = Column(String(255), nullable=False)
    question_text = Column(Text, nullable=False)
    ideal_answer = Column(Text, nullable=False)
    max_marks = Column(Float, nullable=False)
    passing_threshold = Column(Float, default=60.0)  # Percentage
    difficulty_level = Column(String(50), default="intermediate")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    key_concepts = relationship("KeyConcept", back_populates="question", cascade="all, delete-orphan")
    rubric_criteria = relationship("RubricCriteria", back_populates="question", cascade="all, delete-orphan")
    student_answers = relationship("StudentAnswer", back_populates="question")


class KeyConcept(Base):
    """Key concepts extracted from ideal answers"""
    __tablename__ = "key_concepts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    concept_name = Column(String(255), nullable=False)
    concept_description = Column(Text, nullable=False)
    importance_score = Column(Float, nullable=False)  # 0.0 to 1.0
    keywords = Column(Text)  # JSON array of keywords
    max_points = Column(Float, nullable=False)
    extraction_method = Column(String(50), default="llm_extracted")  # llm_extracted, manual
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="key_concepts")
    concept_evaluations = relationship("ConceptEvaluation", back_populates="key_concept")


class RubricCriteria(Base):
    """Grading rubric criteria for questions"""
    __tablename__ = "rubric_criteria"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    criteria_name = Column(String(255), nullable=False)
    criteria_description = Column(Text, nullable=False)
    max_points = Column(Float, nullable=False)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="rubric_criteria")


class StudentAnswer(Base):
    """Student submitted answers"""
    __tablename__ = "student_answers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    answer_id = Column(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(255), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String(10), default="en")
    word_count = Column(Integer)
    
    # Relationships
    question = relationship("Question", back_populates="student_answers")
    grading_results = relationship("GradingResult", back_populates="student_answer")


class GradingResult(Base):
    """AI grading results"""
    __tablename__ = "grading_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    student_answer_id = Column(Integer, ForeignKey("student_answers.id"), nullable=False)
    
    # Scores
    total_score = Column(Float, nullable=False)
    max_possible_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    
    # AI Analysis Metrics
    semantic_similarity = Column(Float, nullable=False)  # 0.0 to 1.0
    coherence_score = Column(Float, nullable=False)
    completeness_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    # Feedback
    detailed_feedback = Column(Text, nullable=False)
    strengths = Column(Text)  # JSON array
    weaknesses = Column(Text)  # JSON array
    suggestions = Column(Text)  # JSON array
    
    # Metadata
    grading_model = Column(String(100), nullable=False)
    processing_time_ms = Column(Float)
    graded_at = Column(DateTime, default=datetime.utcnow)
    graded_by = Column(String(100), default="ai_examiner")
    
    # Additional JSON data for complex structures
    raw_llm_response = Column(Text)  # Store the full LLM response
    criteria_scores = Column(Text)  # JSON of individual criteria scores
    
    # Relationships
    student_answer = relationship("StudentAnswer", back_populates="grading_results")
    concept_evaluations = relationship("ConceptEvaluation", back_populates="grading_result")


class ConceptEvaluation(Base):
    """Evaluation of individual key concepts in student answers"""
    __tablename__ = "concept_evaluations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    grading_result_id = Column(Integer, ForeignKey("grading_results.id"), nullable=False)
    key_concept_id = Column(Integer, ForeignKey("key_concepts.id"), nullable=False)
    
    # Evaluation Results
    present = Column(Boolean, nullable=False)
    accuracy_score = Column(Float, nullable=False)  # 0.0 to 1.0
    points_awarded = Column(Float, nullable=False)
    points_possible = Column(Float, nullable=False)
    
    # Evidence and Reasoning
    explanation = Column(Text, nullable=False)
    evidence_text = Column(Text)  # Quote from student answer
    reasoning = Column(Text)  # Why this score was awarded
    
    # Metadata
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    grading_result = relationship("GradingResult", back_populates="concept_evaluations")
    key_concept = relationship("KeyConcept", back_populates="concept_evaluations")


class GradingSession(Base):
    """Track grading sessions and batches"""
    __tablename__ = "grading_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    batch_name = Column(String(255))
    total_answers = Column(Integer, default=0)
    completed_answers = Column(Integer, default=0)
    failed_answers = Column(Integer, default=0)
    
    # Session Metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    total_processing_time_ms = Column(Float)
    average_score = Column(Float)
    
    # Configuration used
    llm_provider = Column(String(50))
    llm_model = Column(String(100))
    grading_temperature = Column(Float)
    
    # Status
    status = Column(String(20), default="in_progress")  # in_progress, completed, failed


class AuditLog(Base):
    """Audit log for all system operations"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    
    # Event Details
    event_type = Column(String(100), nullable=False)  # grading, concept_extraction, etc.
    entity_type = Column(String(100))  # question, student_answer, grading_result
    entity_id = Column(String(255))
    
    # Event Data
    event_data = Column(Text)  # JSON data
    result_status = Column(String(20))  # success, failure, warning
    error_message = Column(Text)
    
    # Metadata
    user_id = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time_ms = Column(Float)
