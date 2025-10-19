"""
AI Examiner System - Usage Examples
Demonstrates how to use the AI Examiner for grading narrative answers
"""
import asyncio
import json
from datetime import datetime

# Add src to path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.schemas import (
    IdealAnswer, StudentAnswer, GradingRubric, GradingCriteria,
    GradingRequest, KeyConcept
)
from src.services.grading_service import ai_examiner
from src.utils.config import settings


def create_physics_rubric():
    """Create an example physics grading rubric"""
    return GradingRubric(
        subject="Physics",
        topic="Newton's Laws of Motion",
        criteria=[
            GradingCriteria(
                name="Understanding of First Law",
                description="Demonstrates clear understanding of Newton's First Law of Motion (Law of Inertia)",
                max_points=25.0,
                weight=1.0
            ),
            GradingCriteria(
                name="Understanding of Second Law", 
                description="Correctly explains Newton's Second Law (F = ma) and its applications",
                max_points=25.0,
                weight=1.0
            ),
            GradingCriteria(
                name="Understanding of Third Law",
                description="Explains Newton's Third Law (action-reaction) with appropriate examples",
                max_points=25.0,
                weight=1.0
            ),
            GradingCriteria(
                name="Clarity and Examples",
                description="Provides clear explanations with relevant real-world examples",
                max_points=25.0,
                weight=1.0
            )
        ],
        total_max_points=100.0,
        passing_threshold=60.0
    )


def create_ideal_answer():
    """Create an example ideal answer"""
    rubric = create_physics_rubric()
    
    ideal_answer = IdealAnswer(
        id="ideal_001",
        question_id="physics_newton_laws_001",
        content="""Newton's three laws of motion are fundamental principles that describe the relationship between forces acting on a body and its motion.

The First Law, also known as the Law of Inertia, states that an object at rest will remain at rest, and an object in motion will continue moving at constant velocity in a straight line, unless acted upon by an unbalanced external force. This explains why passengers in a car feel pushed back when the car accelerates, or why they continue moving forward when the car suddenly stops. The law emphasizes that force is required to change an object's state of motion.

The Second Law establishes the mathematical relationship between force, mass, and acceleration: F = ma (Force equals mass times acceleration). This means that the acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. For example, it takes more force to accelerate a heavy truck than a light car to the same speed. This law allows us to calculate forces and predict motion quantitatively.

The Third Law states that for every action, there is an equal and opposite reaction. These action-reaction force pairs act on different objects simultaneously. When you walk, you push backward against the ground (action), and the ground pushes forward on you with equal force (reaction), propelling you forward. This principle explains how rockets work in space - they expel hot gases downward (action) and experience an upward thrust (reaction).

These three laws work together to explain virtually all mechanical motion, from simple everyday activities to complex engineering applications like spacecraft navigation and automotive design.""",
        rubric=rubric,
        subject="Physics",
        difficulty_level="intermediate"
    )
    
    return ideal_answer


def create_student_answers():
    """Create example student answers with varying quality"""
    
    # Excellent student answer
    excellent_answer = StudentAnswer(
        id="student_001",
        student_id="STU001",
        question_id="physics_newton_laws_001",
        content="""Newton's three laws describe how forces affect motion.

First Law (Inertia): Objects at rest stay at rest and moving objects keep moving at constant speed unless a force changes this. Like when you're in a bus that suddenly stops - you keep moving forward because of inertia. 

Second Law (F=ma): The force on an object equals its mass times acceleration. Heavier objects need more force to speed up. This is why it's harder to push a full shopping cart than an empty one.

Third Law (Action-Reaction): Every action has an equal opposite reaction. When I jump, I push down on the ground and it pushes up on me with the same force. Rockets work this way - they push gas down and get pushed up.

These laws explain everyday things like why we wear seatbelts (first law), why trucks accelerate slowly (second law), and how we walk (third law).""",
        submitted_at=datetime.now()
    )
    
    # Good student answer (missing some details)
    good_answer = StudentAnswer(
        id="student_002", 
        student_id="STU002",
        question_id="physics_newton_laws_001",
        content="""Newton made three laws about motion.

The first law says things at rest stay at rest and moving things keep moving unless something stops them. This is called inertia.

The second law is F = ma. Force equals mass times acceleration. If you have more mass, you need more force to accelerate.

The third law says every action has an equal and opposite reaction. When you push something, it pushes back equally.

These laws are important for understanding motion in physics.""",
        submitted_at=datetime.now()
    )
    
    # Poor student answer (incomplete and inaccurate)
    poor_answer = StudentAnswer(
        id="student_003",
        student_id="STU003", 
        question_id="physics_newton_laws_001",
        content="""Newton's laws are about forces and motion.

First law is about inertia - things don't move unless you push them.

Second law is F = ma, which means force equals mass and acceleration.

Third law says forces are equal and opposite.

These laws help explain physics.""",
        submitted_at=datetime.now()
    )
    
    return [excellent_answer, good_answer, poor_answer]


async def demonstrate_grading():
    """Demonstrate the AI grading system"""
    print("=== AI Examiner System - Grading Demonstration ===\n")
    
    # Create test data
    ideal_answer = create_ideal_answer()
    student_answers = create_student_answers()
    
    print(f"Question: Explain Newton's Three Laws of Motion")
    print(f"Subject: {ideal_answer.subject}")
    print(f"Max Score: {ideal_answer.rubric.total_max_points}")
    print(f"Passing Threshold: {ideal_answer.rubric.passing_threshold}%\n")
    
    # Grade each student answer
    for i, student_answer in enumerate(student_answers, 1):
        print(f"--- Grading Student {student_answer.student_id} ---")
        print(f"Answer Length: {len(student_answer.content)} characters")
        
        try:
            # Create grading request
            grading_request = GradingRequest(
                student_answer=student_answer,
                ideal_answer=ideal_answer
            )
            
            # Grade the answer
            result = await ai_examiner.grade_answer(
                student_answer=student_answer,
                ideal_answer=ideal_answer,
                use_chain_of_thought=True
            )
            
            # Display results
            print(f"\n📊 GRADING RESULTS:")
            print(f"   Total Score: {result.total_score:.1f}/{result.max_possible_score}")
            print(f"   Percentage: {result.percentage:.1f}%")
            print(f"   Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
            print(f"   Confidence: {result.confidence_score:.2f}")
            
            print(f"\n🔍 ANALYSIS:")
            print(f"   Semantic Similarity: {result.semantic_similarity:.2f}")
            print(f"   Coherence Score: {result.coherence_score:.2f}")
            print(f"   Completeness: {result.completeness_score:.2f}")
            
            print(f"\n📋 CRITERIA SCORES:")
            for criterion, score in result.criteria_scores.items():
                print(f"   {criterion}: {score}")
            
            print(f"\n💪 STRENGTHS:")
            for strength in result.strengths[:3]:  # Show top 3
                print(f"   • {strength}")
            
            print(f"\n⚠️  AREAS FOR IMPROVEMENT:")
            for weakness in result.weaknesses[:3]:  # Show top 3
                print(f"   • {weakness}")
            
            print(f"\n💡 SUGGESTIONS:")
            for suggestion in result.suggestions[:2]:  # Show top 2
                print(f"   • {suggestion}")
            
            print(f"\n📝 DETAILED FEEDBACK:")
            print(f"   {result.detailed_feedback}")
            
            print("\n" + "="*80 + "\n")
            
        except Exception as e:
            print(f"❌ Error grading student {student_answer.student_id}: {e}\n")


async def demonstrate_concept_extraction():
    """Demonstrate key concept extraction"""
    print("=== Key Concept Extraction Demonstration ===\n")
    
    ideal_answer = create_ideal_answer()
    
    # Extract key concepts using the LLM service
    from src.services.llm_service import llm_service
    
    try:
        concepts = await llm_service.extract_key_concepts(
            ideal_answer.content,
            ideal_answer.subject,
            ideal_answer.rubric.topic
        )
        
        print(f"Extracted {len(concepts)} key concepts from the ideal answer:\n")
        
        for i, concept in enumerate(concepts, 1):
            print(f"{i}. **{concept['concept']}** (Importance: {concept['importance']:.2f})")
            print(f"   Keywords: {', '.join(concept['keywords'])}")
            print(f"   Explanation: {concept['explanation']}")
            print()
            
    except Exception as e:
        print(f"❌ Error extracting concepts: {e}")


async def main():
    """Main function to run all demonstrations"""
    print("🤖 AI Examiner System - Starting Demonstrations\n")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"LLM Model: {settings.llm_model}")
    print(f"Temperature: {settings.grading_temperature}")
    print("\n" + "="*80 + "\n")
    
    # Run demonstrations
    await demonstrate_concept_extraction()
    print("\n" + "="*80 + "\n")
    await demonstrate_grading()
    
    print("✅ All demonstrations completed!")


if __name__ == "__main__":
    # Ensure you have set up your API keys in .env file before running
    if not settings.openai_api_key and not settings.anthropic_api_key:
        print("❌ Error: No API keys configured!")
        print("Please create a .env file with your OpenAI or Anthropic API key.")
        print("Example .env content:")
        print("OPENAI_API_KEY=your_key_here")
        print("LLM_PROVIDER=openai")
        print("LLM_MODEL=gpt-4")
        exit(1)
    
    # Run the demonstration
    asyncio.run(main())