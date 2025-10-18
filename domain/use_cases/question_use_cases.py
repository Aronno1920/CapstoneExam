from typing import List, Optional
from ..entities.question import Question
from ..repositories.question_repository import QuestionRepositoryInterface


class QuestionUseCases:
    """Use cases for Question entity following Clean Architecture principles."""
    
    def __init__(self, question_repository: QuestionRepositoryInterface):
        self._question_repository = question_repository
    
    async def create_question(self, question: Question) -> Question:
        """Create a new question."""
        if not question.question or not question.question.strip():
            raise ValueError("Question text cannot be empty")
        
        if question.marks is None or question.marks < 0:
            raise ValueError("Marks must be a non-negative number")
        
        if question.set_id is None:
            raise ValueError("Set ID is required")
        
        if question.category_id is None:
            raise ValueError("Category ID is required")
        
        return await self._question_repository.create(question)
    
    async def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """Get a question by its ID."""
        if question_id <= 0:
            raise ValueError("Question ID must be a positive integer")
        
        return await self._question_repository.get_by_id(question_id)
    
    async def get_all_questions(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Question]:
        """Get all questions with pagination."""
        if skip < 0:
            raise ValueError("Skip must be non-negative")
        
        if limit <= 0 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        return await self._question_repository.get_all(skip, limit, active_only)
    
    async def get_questions_by_set_id(self, set_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by set ID."""
        if set_id <= 0:
            raise ValueError("Set ID must be a positive integer")
        
        return await self._question_repository.get_by_set_id(set_id, skip, limit)
    
    async def get_questions_by_category_id(self, category_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by category ID."""
        if category_id <= 0:
            raise ValueError("Category ID must be a positive integer")
        
        return await self._question_repository.get_by_category_id(category_id, skip, limit)
    
    async def update_question(self, question_id: int, question: Question) -> Optional[Question]:
        """Update an existing question."""
        if question_id <= 0:
            raise ValueError("Question ID must be a positive integer")
        
        if not question.question or not question.question.strip():
            raise ValueError("Question text cannot be empty")
        
        if question.marks is None or question.marks < 0:
            raise ValueError("Marks must be a non-negative number")
        
        # Update timestamp
        question.update_timestamp()
        
        return await self._question_repository.update(question_id, question)
    
    async def delete_question(self, question_id: int) -> bool:
        """Soft delete a question."""
        if question_id <= 0:
            raise ValueError("Question ID must be a positive integer")
        
        return await self._question_repository.delete(question_id)
    
    async def permanently_delete_question(self, question_id: int) -> bool:
        """Permanently delete a question."""
        if question_id <= 0:
            raise ValueError("Question ID must be a positive integer")
        
        return await self._question_repository.hard_delete(question_id)
    
    async def search_questions(self, query: str, skip: int = 0, limit: int = 100) -> List[Question]:
        """Search questions by text content."""
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        
        if skip < 0:
            raise ValueError("Skip must be non-negative")
        
        if limit <= 0 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        return await self._question_repository.search(query.strip(), skip, limit)