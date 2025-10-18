from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import asyncio
from ...shared.config.settings import Settings

# SQLAlchemy Base
Base = declarative_base()
metadata = MetaData()

class DatabaseConnection:
    """Database connection manager for multiple database types."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._sql_engine = None
        self._async_session = None
        self._mongo_client = None
        self._mongo_database = None
    
    def get_sql_connection_string(self) -> str:
        """Get SQL connection string based on database type."""
        db_type = self.settings.database_type.lower()
        
        if db_type == "postgresql":
            return (
                f"postgresql+asyncpg://{self.settings.postgresql_username}:"
                f"{self.settings.postgresql_password}@{self.settings.postgresql_host}:"
                f"{self.settings.postgresql_port}/{self.settings.postgresql_database}"
            )
        elif db_type == "mysql":
            return (
                f"mysql+aiomysql://{self.settings.mysql_username}:"
                f"{self.settings.mysql_password}@{self.settings.mysql_host}:"
                f"{self.settings.mysql_port}/{self.settings.mysql_database}"
            )
        elif db_type == "sqlserver":
            return (
                f"mssql+pyodbc://{self.settings.sqlserver_username}:"
                f"{self.settings.sqlserver_password}@{self.settings.sqlserver_host}:"
                f"{self.settings.sqlserver_port}/{self.settings.sqlserver_database}"
                f"?driver={self.settings.sqlserver_driver.replace(' ', '+')}"
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def get_mongo_connection_string(self) -> str:
        """Get MongoDB connection string."""
        if self.settings.mongodb_username and self.settings.mongodb_password:
            return (
                f"mongodb://{self.settings.mongodb_username}:"
                f"{self.settings.mongodb_password}@{self.settings.mongodb_host}:"
                f"{self.settings.mongodb_port}/{self.settings.mongodb_database}"
            )
        else:
            return f"mongodb://{self.settings.mongodb_host}:{self.settings.mongodb_port}"
    
    async def get_sql_engine(self):
        """Get or create SQL engine."""
        if self._sql_engine is None:
            connection_string = self.get_sql_connection_string()
            self._sql_engine = create_async_engine(
                connection_string,
                echo=self.settings.debug,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300
            )
        return self._sql_engine
    
    async def get_sql_session(self) -> AsyncSession:
        """Get SQL database session."""
        if self._async_session is None:
            engine = await self.get_sql_engine()
            self._async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
        return self._async_session()
    
    async def get_mongo_client(self):
        """Get or create MongoDB client."""
        if self._mongo_client is None:
            connection_string = self.get_mongo_connection_string()
            self._mongo_client = AsyncIOMotorClient(connection_string)
        return self._mongo_client
    
    async def get_mongo_database(self):
        """Get MongoDB database."""
        if self._mongo_database is None:
            client = await self.get_mongo_client()
            self._mongo_database = client[self.settings.mongodb_database]
        return self._mongo_database
    
    async def close_connections(self):
        """Close all database connections."""
        if self._sql_engine:
            await self._sql_engine.dispose()
        
        if self._mongo_client:
            self._mongo_client.close()
    
    def is_sql_database(self) -> bool:
        """Check if the current database is SQL-based."""
        return self.settings.database_type.lower() in ["postgresql", "mysql", "sqlserver"]
    
    def is_mongo_database(self) -> bool:
        """Check if the current database is MongoDB."""
        return self.settings.database_type.lower() == "mongodb"


# Global connection instance
_db_connection: Optional[DatabaseConnection] = None

def get_database_connection(settings: Settings) -> DatabaseConnection:
    """Get global database connection instance."""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection(settings)
    return _db_connection