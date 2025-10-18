import asyncio
from typing import List, Optional
from sqlalchemy import create_engine, select, update, delete, and_, or_
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from domain.entities.question import Question
from domain.repositories.question_repository import QuestionRepositoryInterface
from ..database.models import QuestionModel
from datetime import datetime


def run_in_thread_pool(func):
    """Decorator to run sync functions in thread pool for async compatibility."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
    return wrapper


class SQLServerQuestionRepository(QuestionRepositoryInterface):
    """SQL Server implementation using sync operations with async wrapper."""
    
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string, echo=False)
        self.Session = sessionmaker(bind=self.engine)
    
    def _model_to_entity(self, model: QuestionModel) -> Question:
        """Convert SQLAlchemy model to domain entity."""
        return Question(
            question_id=model.question_id,
            set_id=model.set_id,
            category_id=model.category_id,
            question=model.question,
            narrative_answer=model.narrative_answer,
            marks=model.marks,
            is_update=model.is_update,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def _entity_to_model(self, entity: Question, model: Optional[QuestionModel] = None) -> QuestionModel:
        """Convert domain entity to SQLAlchemy model."""
        if model is None:
            model = QuestionModel()
        
        if entity.question_id is not None:
            model.question_id = entity.question_id
        model.set_id = entity.set_id
        model.category_id = entity.category_id
        model.question = entity.question
        model.narrative_answer = entity.narrative_answer
        model.marks = entity.marks
        model.is_update = entity.is_update
        model.is_active = entity.is_active
        
        if entity.created_at is not None:
            model.created_at = entity.created_at
        if entity.updated_at is not None:
            model.updated_at = entity.updated_at
        
        return model
    
    @run_in_thread_pool
    def _sync_create(self, question: Question) -> Question:
        """Sync create operation."""
        with self.Session() as session:
            model = self._entity_to_model(question)
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._model_to_entity(model)
    
    async def create(self, question: Question) -> Question:
        """Create a new question."""
        return await self._sync_create(question)
    
    @run_in_thread_pool
    def _sync_get_by_id(self, question_id: int) -> Optional[Question]:
        """Sync get by ID operation."""
        with self.Session() as session:
            model = session.query(QuestionModel).filter(QuestionModel.question_id == question_id).first()
            return self._model_to_entity(model) if model else None
    
    async def get_by_id(self, question_id: int) -> Optional[Question]:
        """Get question by ID."""
        return await self._sync_get_by_id(question_id)
    
    @run_in_thread_pool
    def _sync_get_all(self, skip: int, limit: int, active_only: bool) -> List[Question]:
        """Sync get all operation."""
        with self.Session() as session:
            query = session.query(QuestionModel)
            
            if active_only:
                query = query.filter(QuestionModel.is_active == True)
            
            models = query.offset(skip).limit(limit).order_by(QuestionModel.created_at.desc()).all()
            return [self._model_to_entity(model) for model in models]
    
    async def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Question]:
        """Get all questions with pagination."""
        return await self._sync_get_all(skip, limit, active_only)
    
    @run_in_thread_pool
    def _sync_get_by_set_id(self, set_id: int, skip: int, limit: int) -> List[Question]:
        """Sync get by set ID operation."""
        with self.Session() as session:
            models = session.query(QuestionModel).filter(
                and_(
                    QuestionModel.set_id == set_id,
                    QuestionModel.is_active == True
                )
            ).offset(skip).limit(limit).order_by(QuestionModel.created_at.desc()).all()
            
            return [self._model_to_entity(model) for model in models]
    
    async def get_by_set_id(self, set_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by set ID."""
        return await self._sync_get_by_set_id(set_id, skip, limit)
    
    @run_in_thread_pool
    def _sync_get_by_category_id(self, category_id: int, skip: int, limit: int) -> List[Question]:
        """Sync get by category ID operation."""
        with self.Session() as session:
            models = session.query(QuestionModel).filter(
                and_(
                    QuestionModel.category_id == category_id,
                    QuestionModel.is_active == True
                )
            ).offset(skip).limit(limit).order_by(QuestionModel.created_at.desc()).all()
            
            return [self._model_to_entity(model) for model in models]
    
    async def get_by_category_id(self, category_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by category ID."""
        return await self._sync_get_by_category_id(category_id, skip, limit)
    
    @run_in_thread_pool
    def _sync_update(self, question_id: int, question: Question) -> Optional[Question]:
        """Sync update operation."""
        with self.Session() as session:
            model = session.query(QuestionModel).filter(QuestionModel.question_id == question_id).first()
            
            if not model:
                return None
            
            updated_model = self._entity_to_model(question, model)
            updated_model.updated_at = datetime.utcnow()
            updated_model.is_update = True
            
            session.commit()
            session.refresh(updated_model)
            return self._model_to_entity(updated_model)
    
    async def update(self, question_id: int, question: Question) -> Optional[Question]:
        """Update an existing question."""
        return await self._sync_update(question_id, question)
    
    @run_in_thread_pool
    def _sync_delete(self, question_id: int) -> bool:
        """Sync soft delete operation."""
        with self.Session() as session:
            result = session.query(QuestionModel).filter(
                QuestionModel.question_id == question_id
            ).update({
                "is_active": False,
                "is_update": True,
                "updated_at": datetime.utcnow()
            })
            session.commit()
            return result > 0
    
    async def delete(self, question_id: int) -> bool:
        """Soft delete a question."""
        return await self._sync_delete(question_id)
    
    @run_in_thread_pool
    def _sync_hard_delete(self, question_id: int) -> bool:
        """Sync hard delete operation."""
        with self.Session() as session:
            result = session.query(QuestionModel).filter(
                QuestionModel.question_id == question_id
            ).delete()
            session.commit()
            return result > 0
    
    async def hard_delete(self, question_id: int) -> bool:
        """Permanently delete a question."""
        return await self._sync_hard_delete(question_id)
    
    @run_in_thread_pool
    def _sync_search(self, query: str, skip: int, limit: int) -> List[Question]:
        """Sync search operation."""
        with self.Session() as session:
            search_term = f"%{query}%"
            models = session.query(QuestionModel).filter(
                and_(
                    or_(
                        QuestionModel.question.ilike(search_term),
                        QuestionModel.narrative_answer.ilike(search_term)
                    ),
                    QuestionModel.is_active == True
                )
            ).offset(skip).limit(limit).order_by(QuestionModel.created_at.desc()).all()
            
            return [self._model_to_entity(model) for model in models]
    
    async def search(self, query: str, skip: int = 0, limit: int = 100) -> List[Question]:
        """Search questions by text content."""
        return await self._sync_search(query, skip, limit)