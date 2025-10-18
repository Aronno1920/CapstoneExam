from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class QuestionCreate(BaseModel):
    """Schema for creating a new question."""
    set_id: int = Field(..., description="ID of the question set", gt=0)
    category_id: int = Field(..., description="ID of the category", gt=0)
    question: str = Field(..., description="The question text", min_length=1, max_length=2000)
    narrative_answer: Optional[str] = Field(None, description="Optional narrative answer", max_length=5000)
    marks: float = Field(..., description="Marks for the question", ge=0)
    is_active: bool = Field(True, description="Whether the question is active")


class QuestionUpdate(BaseModel):
    """Schema for updating an existing question."""
    set_id: Optional[int] = Field(None, description="ID of the question set", gt=0)
    category_id: Optional[int] = Field(None, description="ID of the category", gt=0)
    question: Optional[str] = Field(None, description="The question text", min_length=1, max_length=2000)
    narrative_answer: Optional[str] = Field(None, description="Optional narrative answer", max_length=5000)
    marks: Optional[float] = Field(None, description="Marks for the question", ge=0)
    is_active: Optional[bool] = Field(None, description="Whether the question is active")


class QuestionResponse(BaseModel):
    """Schema for question response."""
    question_id: int = Field(..., description="Unique identifier for the question")
    set_id: int = Field(..., description="ID of the question set")
    category_id: int = Field(..., description="ID of the category")
    question: str = Field(..., description="The question text")
    narrative_answer: Optional[str] = Field(None, description="Optional narrative answer")
    marks: float = Field(..., description="Marks for the question")
    is_update: bool = Field(..., description="Whether the question has been updated")
    is_active: bool = Field(..., description="Whether the question is active")
    created_at: datetime = Field(..., description="When the question was created")
    updated_at: datetime = Field(..., description="When the question was last updated")

    class Config:
        from_attributes = True


class QuestionList(BaseModel):
    """Schema for paginated list of questions."""
    questions: List[QuestionResponse] = Field(..., description="List of questions")
    total: int = Field(..., description="Total number of questions")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class QuestionSearch(BaseModel):
    """Schema for question search parameters."""
    query: str = Field(..., description="Search query", min_length=1, max_length=100)
    skip: int = Field(0, description="Number of items to skip", ge=0)
    limit: int = Field(100, description="Maximum number of items to return", ge=1, le=1000)


class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Whether the operation was successful")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")