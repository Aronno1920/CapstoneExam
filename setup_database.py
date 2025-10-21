#!/usr/bin/env python3
"""
Database Setup Script for AI Examiner System
This script helps configure and test the database connection.
"""

import os
import sys
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from src.utils.config import settings

def test_database_connection():
    """Test database connection with current settings"""
    print("Testing database connection...")
    print(f"Server: {settings.db_server}")
    print(f"Port: {settings.db_port}")
    print(f"Database: {settings.db_name}")
    print(f"Username: {settings.db_username}")
    print(f"Use Windows Auth: {settings.use_windows_auth}")
    print(f"Driver: {settings.db_driver}")
    
    try:
        # Build connection string
        if settings.use_windows_auth:
            driver = quote_plus(settings.db_driver)
            db_url = f"mssql+pyodbc://@{settings.db_server},{settings.db_port}/{settings.db_name}?driver={driver}&trusted_connection=yes"
        else:
            driver = quote_plus(settings.db_driver)
            username = quote_plus(settings.db_username)
            password = quote_plus(settings.db_password)
            db_url = f"mssql+pyodbc://{username}:{password}@{settings.db_server},{settings.db_port}/{settings.db_name}?driver={driver}"
        
        print(f"\nConnection string: {db_url}")
        
        # Test connection
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection successful!")
                return True
            else:
                print("❌ Database connection failed - unexpected result")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure SQL Server is running")
        print("2. Check if SQL Server is configured to accept remote connections")
        print("3. Verify the server name and port")
        print("4. Check if the database exists")
        print("5. Verify credentials (username/password)")
        print("6. Make sure ODBC Driver 17 for SQL Server is installed")
        return False

def check_sql_server_services():
    """Check if SQL Server services are running (Windows)"""
    print("\nChecking SQL Server services...")
    try:
        import subprocess
        result = subprocess.run(['sc', 'query', 'MSSQLSERVER'], 
                              capture_output=True, text=True, shell=True)
        if 'RUNNING' in result.stdout:
            print("✅ SQL Server service is running")
        else:
            print("❌ SQL Server service is not running")
            print("Please start SQL Server service or check if it's installed")
    except Exception as e:
        print(f"Could not check SQL Server service: {e}")

def main():
    """Main setup function"""
    print("AI Examiner Database Setup")
    print("=" * 40)
    
    # Check SQL Server services
    check_sql_server_services()
    
    # Test database connection
    success = test_database_connection()
    
    if not success:
        print("\n" + "=" * 40)
        print("SETUP INSTRUCTIONS:")
        print("=" * 40)
        print("1. Install SQL Server (if not already installed)")
        print("2. Install ODBC Driver 17 for SQL Server")
        print("3. Start SQL Server service")
        print("4. Create the database using the script in docs/init_database.sql")
        print("5. Configure SQL Server to accept remote connections")
        print("6. Update the database settings in src/utils/config.py or create a .env file")
        print("\nFor Windows Authentication, set USE_WINDOWS_AUTH=true")
        print("For SQL Server Authentication, set USE_WINDOWS_AUTH=false")
        
        return False
    else:
        print("\n✅ Database setup is complete!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
