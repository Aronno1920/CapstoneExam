"""
SQLAlchemy Database Manager for MSSQL Server Integration (raw SQL usage)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Database connection and session management
class DatabaseManager:

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.SessionLocal = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database connection"""
        try:
            self.engine = create_engine(
                self.connection_string,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self):
        """Get a database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()


# Global database manager instance (will be initialized in config)
db_manager: DatabaseManager = None # type: ignore
