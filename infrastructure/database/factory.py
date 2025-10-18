from ...domain.repositories.question_repository import QuestionRepositoryInterface
from ...shared.config.settings import Settings
from ..repositories.sql_question_repository import SQLQuestionRepository
from ..repositories.mongo_question_repository import MongoQuestionRepository
from .connection import get_database_connection


class RepositoryFactory:
    """Factory class to create repository instances based on database type."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_connection = get_database_connection(settings)
    
    async def create_question_repository(self) -> QuestionRepositoryInterface:
        """Create and return a question repository based on database type."""
        db_type = self.settings.database_type.lower()
        
        if db_type in ["postgresql", "mysql", "sqlserver"]:
            session = await self.db_connection.get_sql_session()
            return SQLQuestionRepository(session)
        
        elif db_type == "mongodb":
            database = await self.db_connection.get_mongo_database()
            return MongoQuestionRepository(database)
        
        else:
            raise ValueError(f"Unsupported database type: {db_type}")


# Global factory instance
_repository_factory = None

def get_repository_factory(settings: Settings) -> RepositoryFactory:
    """Get global repository factory instance."""
    global _repository_factory
    if _repository_factory is None:
        _repository_factory = RepositoryFactory(settings)
    return _repository_factory