from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Question:
    """Question domain entity following Clean Architecture principles."""
    
    question_id: Optional[int] = None
    set_id: int = None
    category_id: int = None
    question: str = None
    narrative_answer: Optional[str] = None
    marks: float = None
    is_update: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def update_timestamp(self):
        """Update the timestamp when the entity is modified."""
        self.updated_at = datetime.utcnow()
        self.is_update = True
    
    def deactivate(self):
        """Soft delete by setting is_active to False."""
        self.is_active = False
        self.update_timestamp()
    
    def activate(self):
        """Activate the question."""
        self.is_active = True
        self.update_timestamp()