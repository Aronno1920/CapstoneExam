"""
LLM Operations Router
Handles all LLM-related endpoints for AI grading (in-memory, no database)
"""
import time
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, status

from ...models.schemas import (
    GradingRequest, GradingResponse, BatchGradingRequest, BatchGradingResponse,
    IdealAnswer, StudentAnswer, GradingResult
)
from ...services.grade_service import GradeService, GradingError
from ...services.llm_service import llm_service, LLMError

# Initialize grade service (in-memory, no database required)
gradeService = GradeService(None)

logger = logging.getLogger(__name__)

# Router for LLM operations
router = APIRouter(
    prefix="/llm",
    tags=["LLM Operations"],
    responses={404: {"description": "Not found"}},
)


# Core LLM Grading Endpoints (In-Memory)

@router.post("/grade", response_model=GradingResponse)
async def grade_answer(request: GradingRequest) -> GradingResponse:
    """
    Grade a single student answer against an ideal answer (in-memory processing)
    
    This endpoint performs comprehensive AI-powered grading using Chain-of-Thought reasoning
    to evaluate narrative answers based on semantic understanding and grading rubrics.
    Does not require database connection.
    """
    start_time = time.time()
    
    try:
        logger.info(f"LLM grading request received for student: {request.student_answer.student_id}")
        
        # Perform grading using in-memory AI examiner
        result = await gradeService.grade_answer(
            student_answer=request.student_answer,
            ideal_answer=request.ideal_answer,
            use_chain_of_thought=True
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"LLM grading completed for student {request.student_answer.student_id} "
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
        logger.error(f"LLM grading failed: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM grading failed: {str(e)}"
        )


@router.post("/grade/batch", response_model=BatchGradingResponse)
async def batch_grade_answers(request: BatchGradingRequest) -> BatchGradingResponse:
    """
    Grade multiple student answers in batch (in-memory processing)
    
    Efficiently processes multiple grading requests in parallel while maintaining
    individual error handling for each request. Does not require database.
    """
    logger.info(f"LLM batch grading request received for {len(request.requests)} answers")
    
    try:
        result = await gradeService.batch_grade(request)
        
        logger.info(
            f"LLM batch grading completed: {result.total_successful} successful, "
            f"{result.total_failed} failed in {result.total_processing_time_ms:.2f}ms"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"LLM batch grading failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM batch grading failed: {str(e)}"
        )


# LLM Analysis Endpoints
@router.post("/analyze/concepts")
async def extract_key_concepts(ideal_answer: IdealAnswer) -> Dict[str, Any]:
    """
    Extract key concepts from an ideal answer using LLM
    
    Useful for testing and understanding what concepts the AI identifies
    in reference answers. Pure LLM operation, no database required.
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
            "concept_count": len(concepts),
            "subject": ideal_answer.subject,
            "topic": ideal_answer.rubric.topic
        }
        
    except Exception as e:
        logger.error(f"LLM concept extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM concept extraction failed: {str(e)}"
        )


@router.post("/analyze/similarity")
async def analyze_semantic_similarity(ideal_answer: IdealAnswer, student_answer: StudentAnswer) -> Dict[str, Any]:
    """
    Analyze semantic similarity between ideal and student answers using LLM
    
    Returns detailed semantic analysis without full grading.
    Pure LLM operation, no database required.
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
            "processing_time_ms": processing_time,
            "student_id": student_answer.student_id,
            "question_id": student_answer.question_id
        }
        
    except Exception as e:
        logger.error(f"LLM similarity analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM similarity analysis failed: {str(e)}"
        )


# LLM Provider Management
@router.get("/provider/info")
async def get_provider_info() -> Dict[str, Any]:
    """Get information about the current LLM provider and configuration"""
    return llm_service.get_provider_info()

@router.post("/provider/test")
async def test_provider_connection() -> Dict[str, Any]:
    """Test the connection to the LLM provider"""
    try:
        start_time = time.time()
        connected = llm_service.validate_connection()
        test_time = (time.time() - start_time) * 1000
        
        return {
            "connected": connected,
            "provider": llm_service.get_provider_info()["provider"],
            "model": llm_service.get_provider_info()["model"],
            "test_time_ms": test_time,
            "status": "healthy" if connected else "unhealthy"
        }
        
    except Exception as e:
        logger.error(f"LLM provider test failed: {e}")
        return {
            "connected": False,
            "provider": "unknown",
            "model": "unknown",
            "error": str(e),
            "status": "error"
        }


@router.get("/health")
async def llm_health_check() -> Dict[str, Any]:
    """Check LLM service health"""
    try:
        connected = llm_service.validate_connection()
        provider_info = llm_service.get_provider_info()
        
        return {
            "status": "healthy" if connected else "unhealthy",
            "connected": connected,
            "provider": provider_info.get("provider", "unknown"),
            "model": provider_info.get("model", "unknown"),
            "config": provider_info.get("config", {})
        }
        
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }


# Example Endpoints for Testing
@router.get("/examples/rubric")
async def get_example_rubric() -> Dict[str, Any]:
    """Get an example grading rubric for testing LLM operations"""
    from ...models.schemas import GradingRubric, GradingCriteria
    
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


@router.get("/examples/ideal-answer")
async def get_example_ideal_answer() -> Dict[str, Any]:
    """Get an example ideal answer for testing LLM operations"""
    from ...models.schemas import IdealAnswer, GradingRubric, GradingCriteria
    
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


@router.get("/examples/student-answer")
async def get_example_student_answer() -> Dict[str, Any]:
    """Get an example student answer for testing LLM operations"""
    from ...models.schemas import StudentAnswer
    from datetime import datetime
    
    student_answer = StudentAnswer(
        student_id="STU001",
        question_id="physics_newton_laws_001",
        content="""Newton's three laws explain how forces affect motion.

First Law (Inertia): Objects at rest stay at rest and moving objects keep moving at the same speed unless a force acts on them. Like when you're in a bus that suddenly stops - you keep moving forward because of inertia.

Second Law (F=ma): The force on an object equals its mass times acceleration. Heavier objects need more force to speed up. This is why it's harder to push a full shopping cart than an empty one.

Third Law (Action-Reaction): Every action has an equal and opposite reaction. When I jump, I push down on the ground and it pushes up on me with the same force. Rockets work this way - they push gas down and get pushed up.""",
        submitted_at=datetime.now()
    )
    
    return student_answer.dict()