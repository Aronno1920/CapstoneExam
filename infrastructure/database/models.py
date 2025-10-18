from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from .connection import Base


class QuestionModel(Base):
    """SQLAlchemy model for Question entity."""
    
    __tablename__ = "questions"
    
    question_id = Column(Integer, primary_key=True, autoincrement=True)
    set_id = Column(Integer, nullable=False, index=True)
    category_id = Column(Integer, nullable=False, index=True)
    question = Column(Text, nullable=False)
    narrative_answer = Column(Text, nullable=True)
    marks = Column(Float, nullable=False, default=0.0)
    is_update = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<QuestionModel(id={self.question_id}, question='{self.question[:50]}...', marks={self.marks})>"