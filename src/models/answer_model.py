from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class Answer(BaseModel):
    """Question model for the AI Examiner System"""
    answer_id: int = Field(..., description="Question identifier")
    student_id: int = Field(..., description="Student identifier")
    question_id: int = Field(..., description="Question identifier")
    answer_text: str = Field(..., description="Answer text")
    language: str = Field(..., description="Language")
    word_count: int = Field(..., description="Word count")
    submitted_at: datetime = Field(..., description="Submitted at")