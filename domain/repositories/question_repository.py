from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.question import Question


class QuestionRepositoryInterface(ABC):
    """Abstract repository interface for Question entity following Clean Architecture."""
    
    @abstractmethod
    async def create(self, question: Question) -> Question:
        """Create a new question."""
        pass
    
    @abstractmethod
    async def get_by_id(self, question_id: int) -> Optional[Question]:
        """Get question by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Question]:
        """Get all questions with pagination."""
        pass
    
    @abstractmethod
    async def get_by_set_id(self, set_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by set ID."""
        pass
    
    @abstractmethod
    async def get_by_category_id(self, category_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by category ID."""
        pass
    
    @abstractmethod
    async def update(self, question_id: int, question: Question) -> Optional[Question]:
        """Update an existing question."""
        pass
    
    @abstractmethod
    async def delete(self, question_id: int) -> bool:
        """Soft delete a question (set is_active to False)."""
        pass
    
    @abstractmethod
    async def hard_delete(self, question_id: int) -> bool:
        """Permanently delete a question."""
        pass
    
    @abstractmethod
    async def search(self, query: str, skip: int = 0, limit: int = 100) -> List[Question]:
        """Search questions by text content."""
        pass