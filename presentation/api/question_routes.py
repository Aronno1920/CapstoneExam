from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from ...domain.entities.question import Question
from ...domain.use_cases.question_use_cases import QuestionUseCases
from ..schemas.question_schemas import (
    QuestionCreate, QuestionUpdate, QuestionResponse, 
    QuestionList, QuestionSearch, MessageResponse, ErrorResponse
)
from .dependencies import get_question_use_cases

router = APIRouter()


def _entity_to_response(entity: Question) -> QuestionResponse:
    """Convert domain entity to response schema."""
    return QuestionResponse(
        question_id=entity.question_id,
        set_id=entity.set_id,
        category_id=entity.category_id,
        question=entity.question,
        narrative_answer=entity.narrative_answer,
        marks=entity.marks,
        is_update=entity.is_update,
        is_active=entity.is_active,
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )


@router.post(
    "/",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question",
    description="Create a new question with the provided details"
)
async def create_question(
    question_data: QuestionCreate,
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Create a new question."""
    try:
        # Convert request to domain entity
        question = Question(
            set_id=question_data.set_id,
            category_id=question_data.category_id,
            question=question_data.question,
            narrative_answer=question_data.narrative_answer,
            marks=question_data.marks,
            is_active=question_data.is_active
        )
        
        created_question = await use_cases.create_question(question)
        return _entity_to_response(created_question)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Get question by ID",
    description="Retrieve a specific question by its ID"
)
async def get_question(
    question_id: int,
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Get a question by ID."""
    try:
        question = await use_cases.get_question_by_id(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
        return _entity_to_response(question)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/",
    response_model=List[QuestionResponse],
    summary="Get all questions",
    description="Retrieve all questions with pagination"
)
async def get_all_questions(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    active_only: bool = Query(True, description="Whether to return only active questions"),
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Get all questions with pagination."""
    try:
        questions = await use_cases.get_all_questions(skip, limit, active_only)
        return [_entity_to_response(q) for q in questions]
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/set/{set_id}",
    response_model=List[QuestionResponse],
    summary="Get questions by set ID",
    description="Retrieve all questions belonging to a specific set"
)
async def get_questions_by_set(
    set_id: int,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Get questions by set ID."""
    try:
        questions = await use_cases.get_questions_by_set_id(set_id, skip, limit)
        return [_entity_to_response(q) for q in questions]
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/category/{category_id}",
    response_model=List[QuestionResponse],
    summary="Get questions by category ID",
    description="Retrieve all questions belonging to a specific category"
)
async def get_questions_by_category(
    category_id: int,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Get questions by category ID."""
    try:
        questions = await use_cases.get_questions_by_category_id(category_id, skip, limit)
        return [_entity_to_response(q) for q in questions]
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Update question",
    description="Update an existing question"
)
async def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Update an existing question."""
    try:
        # Get existing question first
        existing_question = await use_cases.get_question_by_id(question_id)
        if not existing_question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
        # Update fields that are provided
        update_data = question_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_question, field, value)
        
        updated_question = await use_cases.update_question(question_id, existing_question)
        if not updated_question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
        return _entity_to_response(updated_question)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{question_id}",
    response_model=MessageResponse,
    summary="Soft delete question",
    description="Soft delete a question (set is_active to False)"
)
async def delete_question(
    question_id: int,
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Soft delete a question."""
    try:
        success = await use_cases.delete_question(question_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
        return MessageResponse(message="Question deleted successfully", success=True)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{question_id}/permanent",
    response_model=MessageResponse,
    summary="Permanently delete question",
    description="Permanently delete a question from the database"
)
async def permanently_delete_question(
    question_id: int,
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Permanently delete a question."""
    try:
        success = await use_cases.permanently_delete_question(question_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
        return MessageResponse(message="Question permanently deleted", success=True)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/search",
    response_model=List[QuestionResponse],
    summary="Search questions",
    description="Search questions by text content"
)
async def search_questions(
    search_params: QuestionSearch,
    use_cases: QuestionUseCases = Depends(get_question_use_cases)
):
    """Search questions by text content."""
    try:
        questions = await use_cases.search_questions(
            search_params.query, 
            search_params.skip, 
            search_params.limit
        )
        return [_entity_to_response(q) for q in questions]
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")