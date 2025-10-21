from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class Question(BaseModel):
    """Question model for the AI Examiner System"""
    question_id: int = Field(..., description="Question identifier")
    subject: str = Field(..., description="Subject area")
    topic: str = Field(..., description="Topic within the subject")
    question_text: str = Field(..., description="The question text")
    ideal_answer: str = Field(..., description="Ideal answer for the question")
    max_marks: float = Field(..., description="Maximum marks for the question")
    passing_threshold: int = Field(..., description="Passing threshold percentage")


class KeyConcept(BaseModel):
    """Key concepts extracted from ideal answers"""
    key_id:int = Field(..., description="Key concept identifier")
    question_id:int = Field(..., description="Question identifier")
    concept_name:str = Field(..., description="Name of the concept")
    concept_description:str = Field(..., description="Description of the concept")
    importance_score:float = Field(..., description="Importance score of the concept")  # 0.0 to 1.0
    keywords:List[str] = Field(..., description="Keywords associated with the concept")
    max_points:float = Field(..., description="Maximum points for the concept")
    created_at:datetime = Field(default_factory=datetime.now, description="Creation timestamp")