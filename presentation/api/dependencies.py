from fastapi import Depends
from ...shared.config.settings import get_settings, Settings
from ...infrastructure.database.factory import get_repository_factory, RepositoryFactory
from ...domain.use_cases.question_use_cases import QuestionUseCases
from ...domain.repositories.question_repository import QuestionRepositoryInterface


async def get_question_repository(
    settings: Settings = Depends(get_settings)
) -> QuestionRepositoryInterface:
    """Dependency to get question repository based on database type."""
    factory = get_repository_factory(settings)
    return await factory.create_question_repository()


async def get_question_use_cases(
    repository: QuestionRepositoryInterface = Depends(get_question_repository)
) -> QuestionUseCases:
    """Dependency to get question use cases."""
    return QuestionUseCases(repository)