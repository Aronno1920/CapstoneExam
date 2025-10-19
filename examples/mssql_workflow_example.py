"""
AI Examiner System - MSSQL Workflow Example
Demonstrates the complete workflow with MSSQL database integration
"""
import asyncio
import urllib.parse
from datetime import datetime

# Add src to path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.database import DatabaseManager
from src.services.database_service import DatabaseService
from src.utils.config import settings


def build_connection_string() -> str:
    """Build MSSQL connection string"""
    # For example purposes - replace with your actual database details
    password = urllib.parse.quote_plus("YourPassword123!")
    driver = urllib.parse.quote_plus("ODBC Driver 17 for SQL Server")
    
    connection_string = (
        f"mssql+pyodbc://sa:{password}@"
        f"localhost:1433/AIExaminerDB"
        f"?driver={driver}"
    )
    return connection_string


async def setup_sample_data(database_service: DatabaseService):
    """Set up sample questions and student answers"""
    print("Setting up sample data...")
    
    # Create sample question
    question = database_service.create_question(
        question_id="PHYS_001",
        subject="Physics",
        topic="Newton's Laws of Motion",
        question_text="Explain Newton's three laws of motion and provide real-world examples for each.",
        ideal_answer="""Newton's three laws of motion are fundamental principles that describe the relationship between forces acting on a body and its motion.

The First Law (Law of Inertia) states that an object at rest will remain at rest, and an object in motion will continue moving at constant velocity in a straight line, unless acted upon by an unbalanced external force. For example, passengers in a car feel pushed back when the car accelerates, or they continue moving forward when the car suddenly stops. The law emphasizes that force is required to change an object's state of motion.

The Second Law establishes the mathematical relationship between force, mass, and acceleration: F = ma (Force equals mass times acceleration). This means that the acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. For example, it takes more force to accelerate a heavy truck than a light car to the same speed.

The Third Law states that for every action, there is an equal and opposite reaction. These action-reaction force pairs act on different objects simultaneously. When you walk, you push backward against the ground (action), and the ground pushes forward on you with equal force (reaction), propelling you forward. This principle explains how rockets work in space.""",
        max_marks=100.0,
        passing_threshold=60.0,
        difficulty_level="intermediate"
    )
    print(f"✅ Created question: {question.question_id}")
    
    # Create sample student answers with varying quality
    student_answers = [
        {
            "student_id": "STU001",
            "answer": """Newton's three laws explain how forces and motion work together.

First Law (Inertia): Objects at rest stay at rest, and moving objects keep moving at the same speed unless a force acts on them. Like when you're in a car that suddenly stops - you keep moving forward because of inertia.

Second Law (F=ma): The force on an object equals its mass times acceleration. Heavier objects need more force to speed up. This is why it's harder to push a full shopping cart than an empty one.

Third Law (Action-Reaction): Every action has an equal and opposite reaction. When I jump, I push down on the ground and it pushes up on me with the same force. Rockets work this way - they push gas down and get pushed up."""
        },
        {
            "student_id": "STU002",
            "answer": """Newton made three laws about motion.

The first law says things at rest stay at rest and moving things keep moving unless something stops them. This is called inertia.

The second law is F = ma. Force equals mass times acceleration. If you have more mass, you need more force to accelerate.

The third law says every action has an equal and opposite reaction. When you push something, it pushes back equally."""
        },
        {
            "student_id": "STU003",
            "answer": """Newton's laws are about forces and motion.

First law is about inertia - things don't move unless you push them.

Second law is F = ma, which means force equals mass and acceleration.

Third law says forces are equal and opposite."""
        }
    ]
    
    for student_data in student_answers:
        student_answer = database_service.create_student_answer(
            student_id=student_data["student_id"],
            question_id="PHYS_001",
            answer_text=student_data["answer"]
        )
        print(f"✅ Created answer for student: {student_answer.student_id}")
    
    return question.question_id


async def demonstrate_workflow(database_service: DatabaseService, question_id: str):
    """Demonstrate the complete grading workflow"""
    print(f"\n{'='*80}")
    print("🤖 AI EXAMINER - MSSQL WORKFLOW DEMONSTRATION")
    print(f"{'='*80}")
    
    student_ids = ["STU001", "STU002", "STU003"]
    
    for i, student_id in enumerate(student_ids, 1):
        print(f"\n--- Grading Student {student_id} ({i}/3) ---")
        
        try:
            # Execute complete workflow
            result = await database_service.complete_grading_workflow(
                question_id=question_id,
                student_id=student_id
            )
            
            # Display results in required format
            print(f"\n📊 GRADING RESULTS:")
            print(f"   Score: {result['Score']}")
            print(f"   Percentage: {result['Percentage']}")
            print(f"   Status: {'✅ PASSED' if result['Passed'] else '❌ FAILED'}")
            print(f"   Processing Time: {result['ProcessingTimeMs']:.2f}ms")
            print(f"   Confidence: {result['ConfidenceScore']:.2f}")
            
            print(f"\n🔍 KEY CONCEPTS COVERED:")
            for concept_result in result['Key_Concepts_Covered']:
                print(f"   • {concept_result}")
            
            print(f"\n📝 JUSTIFICATION:")
            print(f"   {result['Justification']}")
            
            print(f"\n💾 Result ID: {result['GradingResultId']}")
            
        except Exception as e:
            print(f"❌ Error grading student {student_id}: {e}")
        
        print(f"\n{'-'*60}")


async def demonstrate_individual_steps(database_service: DatabaseService, question_id: str):
    """Demonstrate individual workflow steps"""
    print(f"\n{'='*80}")
    print("🔧 INDIVIDUAL WORKFLOW STEPS DEMONSTRATION")
    print(f"{'='*80}")
    
    # Step 1: Retrieve ideal answer and marks
    print("\n📖 Step 1: Retrieve Ideal Answer and Marks")
    question = database_service.get_question_with_ideal_answer(question_id)
    print(f"   Question ID: {question.question_id}")
    print(f"   Subject: {question.subject}")
    print(f"   Max Marks: {question.max_marks}")
    print(f"   Ideal Answer Length: {len(question.ideal_answer)} characters")
    
    # Step 2: Extract and save key concepts
    print("\n🧠 Step 2: Extract and Save Key Concepts (Semantic Understanding)")
    key_concepts = await database_service.extract_and_save_key_concepts(question)
    print(f"   Extracted {len(key_concepts)} key concepts:")
    for i, concept in enumerate(key_concepts, 1):
        print(f"     {i}. {concept.concept_name} (Importance: {concept.importance_score:.2f}, Points: {concept.max_points})")
    
    # Step 3: Retrieve student answer
    print(f"\n👨‍🎓 Step 3: Retrieve Student Answer")
    student_answer = database_service.get_student_answer("STU001", question_id)
    print(f"   Student ID: {student_answer.student_id}")
    print(f"   Answer Length: {len(student_answer.answer_text)} characters")
    print(f"   Word Count: {student_answer.word_count}")
    print(f"   Submitted: {student_answer.submitted_at}")
    
    # Step 4 would be the grading - already demonstrated above
    print(f"\n✅ Step 4: Grading and saving is demonstrated in the workflow above")


async def main():
    """Main function to run all demonstrations"""
    print("🚀 AI Examiner MSSQL Integration - Starting Demonstrations")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"LLM Model: {settings.llm_model}")
    
    # Check API keys
    if not settings.openai_api_key and not settings.anthropic_api_key:
        print("❌ Error: No API keys configured!")
        print("Please set up your .env file with API keys.")
        return
    
    try:
        # Initialize database connection
        connection_string = build_connection_string()
        print(f"📊 Connecting to MSSQL database...")
        
        db_manager = DatabaseManager(connection_string)
        database_service = DatabaseService(db_manager)
        
        print("✅ Database connected successfully!")
        
        # Set up sample data
        question_id = await setup_sample_data(database_service)
        
        # Demonstrate individual steps
        await demonstrate_individual_steps(database_service, question_id)
        
        # Demonstrate complete workflow
        await demonstrate_workflow(database_service, question_id)
        
        print(f"\n{'='*80}")
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print("\n📋 WORKFLOW SUMMARY:")
        print("1. ✅ Retrieved ideal answers and marks from MSSQL")
        print("2. ✅ Extracted and saved semantic understanding (key concepts)")
        print("3. ✅ Retrieved student submitted answers")
        print("4. ✅ Graded and saved results in required format:")
        print("   • Score: X/Y format")
        print("   • Justification: Detailed feedback")
        print("   • Key_Concepts_Covered: [Concept A (points) - Reason...]")
        
        # Clean up
        db_manager.close()
        
    except Exception as e:
        print(f"❌ Error in demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 80)
    print("AI EXAMINER SYSTEM - MSSQL INTEGRATION")
    print("Complete Workflow Demonstration")
    print("=" * 80)
    print()
    print("⚠️  IMPORTANT: Update the connection_string in this file with your actual database credentials!")
    print("   - Server name/IP")
    print("   - Database name") 
    print("   - Username/password")
    print("   - ODBC driver version")
    print()
    
    # Uncomment the line below after updating database credentials
    # asyncio.run(main())
    
    print("✏️  After updating the connection string, uncomment the asyncio.run(main()) line and run this script.")