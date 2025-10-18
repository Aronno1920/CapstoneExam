from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import re
from domain.entities.question import Question
from domain.repositories.question_repository import QuestionRepositoryInterface


class MongoQuestionRepository(QuestionRepositoryInterface):
    """MongoDB implementation of QuestionRepositoryInterface."""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database["questions"]
    
    def _document_to_entity(self, document: Dict[str, Any]) -> Question:
        """Convert MongoDB document to domain entity."""
        return Question(
            question_id=document.get("question_id"),
            set_id=document.get("set_id"),
            category_id=document.get("category_id"),
            question=document.get("question"),
            narrative_answer=document.get("narrative_answer"),
            marks=document.get("marks"),
            is_update=document.get("is_update", False),
            is_active=document.get("is_active", True),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at")
        )
    
    def _entity_to_document(self, entity: Question, exclude_id: bool = False) -> Dict[str, Any]:
        """Convert domain entity to MongoDB document."""
        document = {
            "set_id": entity.set_id,
            "category_id": entity.category_id,
            "question": entity.question,
            "narrative_answer": entity.narrative_answer,
            "marks": entity.marks,
            "is_update": entity.is_update,
            "is_active": entity.is_active,
            "created_at": entity.created_at or datetime.utcnow(),
            "updated_at": entity.updated_at or datetime.utcnow()
        }
        
        if not exclude_id and entity.question_id is not None:
            document["question_id"] = entity.question_id
        
        return document
    
    async def _get_next_sequence_value(self) -> int:
        """Get next sequence value for question_id."""
        counter = await self.database["counters"].find_one_and_update(
            {"_id": "question_id"},
            {"$inc": {"sequence_value": 1}},
            upsert=True,
            return_document=True
        )
        return counter["sequence_value"]
    
    async def create(self, question: Question) -> Question:
        """Create a new question."""
        # Generate new question_id
        question.question_id = await self._get_next_sequence_value()
        
        document = self._entity_to_document(question)
        result = await self.collection.insert_one(document)
        
        # Return the created question with the generated ID
        created_document = await self.collection.find_one({"_id": result.inserted_id})
        return self._document_to_entity(created_document)
    
    async def get_by_id(self, question_id: int) -> Optional[Question]:
        """Get question by ID."""
        document = await self.collection.find_one({"question_id": question_id})
        return self._document_to_entity(document) if document else None
    
    async def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Question]:
        """Get all questions with pagination."""
        query = {}
        if active_only:
            query["is_active"] = True
        
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        return [self._document_to_entity(doc) for doc in documents]
    
    async def get_by_set_id(self, set_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by set ID."""
        query = {"set_id": set_id, "is_active": True}
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        return [self._document_to_entity(doc) for doc in documents]
    
    async def get_by_category_id(self, category_id: int, skip: int = 0, limit: int = 100) -> List[Question]:
        """Get questions by category ID."""
        query = {"category_id": category_id, "is_active": True}
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        return [self._document_to_entity(doc) for doc in documents]
    
    async def update(self, question_id: int, question: Question) -> Optional[Question]:
        """Update an existing question."""
        update_data = self._entity_to_document(question, exclude_id=True)
        update_data["updated_at"] = datetime.utcnow()
        update_data["is_update"] = True
        
        result = await self.collection.update_one(
            {"question_id": question_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return None
        
        # Return the updated document
        updated_document = await self.collection.find_one({"question_id": question_id})
        return self._document_to_entity(updated_document)
    
    async def delete(self, question_id: int) -> bool:
        """Soft delete a question (set is_active to False)."""
        result = await self.collection.update_one(
            {"question_id": question_id},
            {
                "$set": {
                    "is_active": False,
                    "is_update": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.matched_count > 0
    
    async def hard_delete(self, question_id: int) -> bool:
        """Permanently delete a question."""
        result = await self.collection.delete_one({"question_id": question_id})
        return result.deleted_count > 0
    
    async def search(self, query: str, skip: int = 0, limit: int = 100) -> List[Question]:
        """Search questions by text content."""
        # Create regex pattern for case-insensitive search
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        
        search_query = {
            "$and": [
                {"is_active": True},
                {
                    "$or": [
                        {"question": {"$regex": pattern}},
                        {"narrative_answer": {"$regex": pattern}}
                    ]
                }
            ]
        }
        
        cursor = self.collection.find(search_query).skip(skip).limit(limit).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        return [self._document_to_entity(doc) for doc in documents]