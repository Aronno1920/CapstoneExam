"""
Test database connection and verify setup for AI Examiner System
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from src.models.database import DatabaseManager, Base
from database.connection_config import DatabaseConfig
import traceback


def test_basic_connection():
    """Test basic database connection"""
    print("Testing basic database connection...")
    try:
        conn_string = DatabaseConfig.get_connection_string()
        engine = create_engine(conn_string, echo=False)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Basic connection successful")
                return True
            else:
                print("❌ Connection test failed")
                return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_database_exists():
    """Test if AIExaminerDB database exists"""
    print("Checking if AIExaminerDB database exists...")
    try:
        conn_string = DatabaseConfig.get_connection_string()
        engine = create_engine(conn_string, echo=False)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DB_NAME() as current_db"))
            row = result.fetchone()
            if row:
                db_name = row[0]
                if db_name == 'AIExaminerDB':
                    print(f"✅ Connected to database: {db_name}")
                    return True
                else:
                    print(f"⚠️  Connected to different database: {db_name}")
                    return False
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False


def test_tables_exist():
    """Test if required tables exist"""
    print("Checking if required tables exist...")
    required_tables = [
        'questions', 'key_concepts', 'rubric_criteria', 
        'student_answers', 'grading_results', 'concept_evaluations',
        'grading_sessions', 'audit_logs'
    ]
    
    try:
        conn_string = DatabaseConfig.get_connection_string()
        engine = create_engine(conn_string, echo=False)
        
        existing_tables = []
        with engine.connect() as conn:
            for table in required_tables:
                result = conn.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = '{table}' AND TABLE_SCHEMA = 'dbo'
                """))
                count = result.fetchone()[0]
                if count > 0:
                    existing_tables.append(table)
        
        print(f"✅ Found {len(existing_tables)}/{len(required_tables)} required tables")
        
        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        else:
            print("✅ All required tables exist")
            return True
            
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False


def test_sample_data():
    """Test if sample data was inserted"""
    print("Checking sample data...")
    try:
        conn_string = DatabaseConfig.get_connection_string()
        engine = create_engine(conn_string, echo=False)
        
        with engine.connect() as conn:
            # Check questions
            result = conn.execute(text("SELECT COUNT(*) FROM questions"))
            question_count = result.fetchone()[0]
            
            # Check key concepts
            result = conn.execute(text("SELECT COUNT(*) FROM key_concepts"))
            concept_count = result.fetchone()[0]
            
            # Check rubric criteria
            result = conn.execute(text("SELECT COUNT(*) FROM rubric_criteria"))
            criteria_count = result.fetchone()[0]
            
            print(f"✅ Sample data found:")
            print(f"   - Questions: {question_count}")
            print(f"   - Key concepts: {concept_count}")
            print(f"   - Rubric criteria: {criteria_count}")
            
            return question_count > 0 and concept_count > 0 and criteria_count > 0
            
    except Exception as e:
        print(f"❌ Sample data check failed: {e}")
        return False


def test_stored_procedures():
    """Test stored procedures"""
    print("Testing stored procedures...")
    try:
        conn_string = DatabaseConfig.get_connection_string()
        engine = create_engine(conn_string, echo=False)
        
        with engine.connect() as conn:
            # Test sp_GetQuestionComplete
            result = conn.execute(text("EXEC sp_GetQuestionComplete @QuestionId = 'PHYS_001'"))
            rows = result.fetchall()
            
            if rows:
                print("✅ sp_GetQuestionComplete works")
            else:
                print("❌ sp_GetQuestionComplete failed")
                return False
            
            # Test sp_GetGradingStatistics
            result = conn.execute(text("EXEC sp_GetGradingStatistics"))
            stats = result.fetchone()
            print("✅ sp_GetGradingStatistics works")
            
            return True
            
    except Exception as e:
        print(f"❌ Stored procedure test failed: {e}")
        return False


def test_views():
    """Test database views"""
    print("Testing database views...")
    try:
        conn_string = DatabaseConfig.get_connection_string()
        engine = create_engine(conn_string, echo=False)
        
        with engine.connect() as conn:
            # Test vw_QuestionSummary
            result = conn.execute(text("SELECT TOP 5 * FROM vw_QuestionSummary"))
            rows = result.fetchall()
            print(f"✅ vw_QuestionSummary: {len(rows)} records")
            
            # Test vw_GradingPerformance (may be empty)
            result = conn.execute(text("SELECT COUNT(*) FROM vw_GradingPerformance"))
            count = result.fetchone()[0]
            print(f"✅ vw_GradingPerformance: {count} records")
            
            return True
            
    except Exception as e:
        print(f"❌ View test failed: {e}")
        return False


def test_database_manager():
    """Test the DatabaseManager class"""
    print("Testing DatabaseManager class...")
    try:
        conn_string = DatabaseConfig.get_connection_string()
        db_manager = DatabaseManager(conn_string)
        
        # Test getting a session
        session = db_manager.get_session()
        if session:
            print("✅ DatabaseManager session created successfully")
            
            # Test a simple query
            from src.models.database import Question
            questions = session.query(Question).limit(5).all()
            print(f"✅ Retrieved {len(questions)} questions using ORM")
            
            session.close()
            return True
        else:
            print("❌ Failed to create DatabaseManager session")
            return False
            
    except Exception as e:
        print(f"❌ DatabaseManager test failed: {e}")
        print(traceback.format_exc())
        return False


def run_all_tests():
    """Run all database tests"""
    print("🚀 Starting AI Examiner Database Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Database Exists", test_database_exists),
        ("Tables Exist", test_tables_exist),
        ("Sample Data", test_sample_data),
        ("Stored Procedures", test_stored_procedures),
        ("Views", test_views),
        ("DatabaseManager", test_database_manager)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database is ready for use.")
    else:
        print("⚠️  Some tests failed. Please check the database setup.")
        print("\n💡 Common solutions:")
        print("   1. Ensure SQL Server is running")
        print("   2. Check connection credentials in connection_config.py")
        print("   3. Run the init_database.sql script first")
        print("   4. Install required Python packages: pip install sqlalchemy pyodbc")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)