from typing import List, Optional
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from domain.entities.question import Question
from domain.repositories.question_repository import QuestionRepositoryInterface
from ..database.models import QuestionModel
from datetime import datetime


class SQLQuestionRepository(QuestionRepositoryInterface):
    """SQL implementation of QuestionRepositoryInterface."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
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
    
    async def create(self, question: Question) -> Question:
        """Create a new question."""
        model = self._entity_to_model(question)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._model_to_entity(model)
    
    async def get_by_id(self, question_id: int) -> Optional[Question]:
        """Get question by ID."""
        stmt = select(QuestionModel).where(QuestionModel.question_id == question_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None
    
    async def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Question]:
        """Get all questions with pagination."""
        stmt = select(QuestionModel)
        
        if active_only:
            stmt = stmt.where(QuestionModel.is_active == True)
        
        stmt = stmt.offset(skip).limit(limit).order_by(QuestionModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]
    
    async def get_by_set_id(self, set_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by set ID."""
        stmt = select(QuestionModel).where(
            and_(
                QuestionModel.set_id == set_id,
                QuestionModel.is_active == True
            )
        ).offset(skip).limit(limit).order_by(QuestionModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]
    
    async def get_by_category_id(self, category_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by category ID."""
        stmt = select(QuestionModel).where(
            and_(
                QuestionModel.category_id == category_id,
                QuestionModel.is_active == True
            )
        ).offset(skip).limit(limit).order_by(QuestionModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]
    
    async def update(self, question_id: int, question: Question) -> Optional[Question]:
        """Update an existing question."""
        stmt = select(QuestionModel).where(QuestionModel.question_id == question_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        # Update the model with new values
        updated_model = self._entity_to_model(question, model)
        updated_model.updated_at = datetime.utcnow()
        updated_model.is_update = True
        
        await self.session.commit()
        await self.session.refresh(updated_model)
        return self._model_to_entity(updated_model)
    
    async def delete(self, question_id: int) -> bool:
        """Soft delete a question (set is_active to False)."""
        stmt = update(QuestionModel).where(
            QuestionModel.question_id == question_id
        ).values(
            is_active=False,
            is_update=True,
            updated_at=datetime.utcnow()
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def hard_delete(self, question_id: int) -> bool:
        """Permanently delete a question."""
        stmt = delete(QuestionModel).where(QuestionModel.question_id == question_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def search(self, query: str, skip: int = 0, limit: int = 100) -> List[Question]:
        """Search questions by text content."""
        search_term = f"%{query}%"
        stmt = select(QuestionModel).where(
            and_(
                or_(
                    QuestionModel.question.ilike(search_term),
                    QuestionModel.narrative_answer.ilike(search_term)
                ),
                QuestionModel.is_active == True
            )
        ).offset(skip).limit(limit).order_by(QuestionModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]