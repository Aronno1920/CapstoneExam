from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class IdealAnswer(BaseModel):
    question_id: int = Field(..., description="Quesiton id")
    subject: str = Field(..., description="")
    ideal_answer: str = Field(..., description="")
    max_marks: float = Field(..., description="")


class Answer(BaseModel):
    """Question model for the AI Examiner System"""
    answer_id: int = Field(..., description="Question identifier")
    student_id: int = Field(..., description="Student identifier")
    question_id: int = Field(..., description="Question identifier")
    answer_text: str = Field(..., description="Answer text")
    language: str = Field(..., description="Language")
    word_count: int = Field(..., description="Word count")
    submitted_at: datetime = Field(..., description="Submitted at")
    
class StudentAnswer(BaseModel):
    answer_id: int = Field(..., description="")
    student_id: int = Field(..., description="")
    question_id: int = Field(..., description="")
    subject: str = Field(..., description="")
    topic: str = Field(..., description="")
    question_text: str = Field(..., description="")
    answer_text: str = Field(..., description="")
    language: str = Field(..., description="")
    word_count: int = Field(..., description="")
    max_marks: float = Field(..., description="")
    passing_threshold: float = Field(..., description="")


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting a student answer"""
    student_id: int = Field(..., description="Student identifier")
    question_id: int = Field(..., description="Question identifier")
    answer_text: str = Field(..., min_length=1, description="Student's answer text")
    language: str = Field(default="en", description="Language of the answer")