"""
FastAPI REST API for AI Examiner System
"""
import logging
import time
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from ..models.schemas import (
    GradingRequest, GradingResponse, BatchGradingRequest, BatchGradingResponse,
    IdealAnswer, StudentAnswer, GradingResult
)
from ..services.grading_service import ai_examiner, GradingError
from ..services.llm_service import llm_service, LLMError
from ..utils.config import settings, validate_api_keys


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting AI Examiner API...")
    
    # Validate API keys
    api_validation = validate_api_keys()
    if not api_validation["selected_provider_valid"]:
        logger.error(f"Invalid API configuration for provider: {settings.llm_provider}")
        raise RuntimeError("LLM API keys not properly configured")
    
    # Test LLM connection
    if not llm_service.validate_connection():
        logger.error("Failed to validate LLM connection")
        raise RuntimeError("Cannot connect to LLM provider")
    
    logger.info("AI Examiner API started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down AI Examiner API...")


# Create FastAPI app
app = FastAPI(
    title="AI Examiner API",
    description="AI-powered narrative answer grading system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(GradingError)
async def grading_error_handler(request, exc: GradingError):
    logger.error(f"Grading error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Grading failed", "detail": str(exc)}
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request, exc: LLMError):
    logger.error(f"LLM error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "LLM service unavailable", "detail": str(exc)}
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including LLM connectivity"""
    llm_connected = llm_service.validate_connection()
    provider_info = llm_service.get_provider_info()
    api_validation = validate_api_keys()
    
    return {
        "status": "healthy" if llm_connected else "degraded",
        "timestamp": time.time(),
        "llm_provider": provider_info,
        "api_keys_valid": api_validation,
        "connected": llm_connected
    }


# Core grading endpoints
@app.post("/grade", response_model=GradingResponse)
async def grade_answer(request: GradingRequest) -> GradingResponse:
    """
    Grade a single student answer against an ideal answer
    
    This endpoint performs comprehensive AI-powered grading using Chain-of-Thought reasoning
    to evaluate narrative answers based on semantic understanding and grading rubrics.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Grading request received for student: {request.student_answer.student_id}")
        
        # Perform grading
        result = await ai_examiner.grade_answer(
            student_answer=request.student_answer,
            ideal_answer=request.ideal_answer,
            use_chain_of_thought=True  # Use recommended Chain-of-Thought approach
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Grading completed for student {request.student_answer.student_id} "
            f"in {processing_time:.2f}ms - Score: {result.percentage:.1f}%"
        )
        
        return GradingResponse(
            result=result,
            processing_time_ms=processing_time,
            success=True,
            error_message=None
        )
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"Grading failed: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grading failed: {str(e)}"
        )


@app.post("/grade/batch", response_model=BatchGradingResponse)
async def batch_grade_answers(request: BatchGradingRequest) -> BatchGradingResponse:
    """
    Grade multiple student answers in batch
    
    Efficiently processes multiple grading requests in parallel while maintaining
    individual error handling for each request.
    """
    logger.info(f"Batch grading request received for {len(request.requests)} answers")
    
    try:
        result = await ai_examiner.batch_grade(request)
        
        logger.info(
            f"Batch grading completed: {result.total_successful} successful, "
            f"{result.total_failed} failed in {result.total_processing_time_ms:.2f}ms"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Batch grading failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch grading failed: {str(e)}"
        )


# Utility endpoints for testing and management
@app.post("/analyze/concepts")
async def extract_key_concepts(ideal_answer: IdealAnswer) -> Dict[str, Any]:
    """
    Extract key concepts from an ideal answer
    
    Useful for testing and understanding what concepts the AI identifies
    in reference answers.
    """
    try:
        start_time = time.time()
        
        concepts = await llm_service.extract_key_concepts(
            ideal_answer.content,
            ideal_answer.subject,
            ideal_answer.rubric.topic
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "key_concepts": concepts,
            "processing_time_ms": processing_time,
            "concept_count": len(concepts)
        }
        
    except Exception as e:
        logger.error(f"Concept extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Concept extraction failed: {str(e)}"
        )


@app.post("/analyze/similarity")
async def analyze_semantic_similarity(
    ideal_answer: IdealAnswer,
    student_answer: StudentAnswer
) -> Dict[str, Any]:
    """
    Analyze semantic similarity between ideal and student answers
    
    Returns detailed semantic analysis without full grading.
    """
    try:
        start_time = time.time()
        
        # First extract key concepts if not present
        key_concepts_data = []
        if ideal_answer.key_concepts:
            key_concepts_data = [
                {
                    "concept": kc.concept,
                    "importance": kc.importance,
                    "keywords": kc.keywords,
                    "explanation": kc.explanation
                }
                for kc in ideal_answer.key_concepts
            ]
        else:
            # Extract concepts on-the-fly
            key_concepts_raw = await llm_service.extract_key_concepts(
                ideal_answer.content,
                ideal_answer.subject,
                ideal_answer.rubric.topic
            )
            key_concepts_data = key_concepts_raw
        
        # Analyze similarity
        similarity_analysis = await llm_service.analyze_semantic_similarity(
            ideal_answer.content,
            student_answer.content,
            key_concepts_data
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "analysis": similarity_analysis,
            "key_concepts": key_concepts_data,
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Similarity analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Similarity analysis failed: {str(e)}"
        )


@app.get("/provider/info")
async def get_provider_info() -> Dict[str, Any]:
    """Get information about the current LLM provider and configuration"""
    return llm_service.get_provider_info()


@app.post("/provider/test")
async def test_provider_connection() -> Dict[str, Any]:
    """Test the connection to the LLM provider"""
    try:
        start_time = time.time()
        connected = llm_service.validate_connection()
        test_time = (time.time() - start_time) * 1000
        
        return {
            "connected": connected,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "test_time_ms": test_time
        }
        
    except Exception as e:
        logger.error(f"Provider test failed: {e}")
        return {
            "connected": False,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "error": str(e)
        }


# Example endpoints for demonstration
@app.get("/examples/rubric")
async def get_example_rubric() -> Dict[str, Any]:
    """Get an example grading rubric for testing"""
    from ..models.schemas import GradingRubric, GradingCriteria
    
    example_rubric = GradingRubric(
        subject="Physics",
        topic="Newton's Laws of Motion",
        criteria=[
            GradingCriteria(
                name="Understanding of First Law",
                description="Demonstrates clear understanding of Newton's First Law (inertia)",
                max_points=25.0,
                weight=1.0
            ),
            GradingCriteria(
                name="Understanding of Second Law",
                description="Correctly explains F=ma and its applications",
                max_points=25.0,
                weight=1.0
            ),
            GradingCriteria(
                name="Understanding of Third Law",
                description="Explains action-reaction pairs with examples",
                max_points=25.0,
                weight=1.0
            ),
            GradingCriteria(
                name="Clarity and Examples",
                description="Clear explanation with relevant real-world examples",
                max_points=25.0,
                weight=1.0
            )
        ],
        total_max_points=100.0,
        passing_threshold=60.0
    )
    
    return example_rubric.dict()


@app.get("/examples/ideal-answer")
async def get_example_ideal_answer() -> Dict[str, Any]:
    """Get an example ideal answer for testing"""
    from ..models.schemas import IdealAnswer, GradingRubric, GradingCriteria
    
    rubric = GradingRubric(
        subject="Physics",
        topic="Newton's Laws of Motion",
        criteria=[
            GradingCriteria(name="First Law", description="Understanding of inertia", max_points=25.0),
            GradingCriteria(name="Second Law", description="F=ma understanding", max_points=25.0),
            GradingCriteria(name="Third Law", description="Action-reaction pairs", max_points=25.0),
            GradingCriteria(name="Examples", description="Clear examples", max_points=25.0)
        ],
        total_max_points=100.0
    )
    
    ideal_answer = IdealAnswer(
        question_id="physics_newton_laws_001",
        content="""Newton's three laws of motion are fundamental principles that describe the relationship between forces and motion.

The First Law (Law of Inertia) states that an object at rest stays at rest and an object in motion stays in motion at constant velocity, unless acted upon by an unbalanced force. For example, a book on a table remains stationary until someone pushes it.

The Second Law quantifies the relationship between force, mass, and acceleration with the equation F = ma. This means that the acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. A heavier object requires more force to achieve the same acceleration as a lighter object.

The Third Law states that for every action, there is an equal and opposite reaction. When you walk, you push backward on the ground, and the ground pushes forward on you with equal force. This is why rockets can propel themselves in space by expelling exhaust gases.

These laws are interconnected and explain everyday phenomena from why we wear seatbelts (First Law) to how rockets work (Third Law) and why it's harder to push a car than a bicycle (Second Law).""",
        rubric=rubric,
        subject="Physics",
        difficulty_level="intermediate"
    )
    
    return ideal_answer.dict()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )