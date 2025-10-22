from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


#############################################
# Request/Response Models
class GradingWorkflowRequest(BaseModel):
    """Request for complete MSSQL grading workflow"""
    question_id: int
    student_id: int


class GradingWorkflowResponse(BaseModel):
    """Response from MSSQL grading workflow"""
    Score: str
    Justification: str
    Key_Concepts_Covered: List[str]
    Percentage: str
    Passed: bool
    ProcessingTimeMs: float
    ConfidenceScore: float
    GradingResultId: str

#############################################