from fastapi import APIRouter
from .api.question_routes import router as question_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(question_router, prefix="/questions", tags=["Questions"])

# You can add more routers here as your application grows
# api_router.include_router(user_router, prefix="/users", tags=["Users"])
# api_router.include_router(category_router, prefix="/categories", tags=["Categories"])
# api_router.include_router(set_router, prefix="/sets", tags=["Sets"])