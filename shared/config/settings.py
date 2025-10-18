from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    database_type: str = "postgresql"  # Default fallback
    
    # SQL Server Configuration
    sqlserver_host: str = "localhost"
    sqlserver_port: int = 1433
    sqlserver_database: str = "capstoneexam"
    sqlserver_username: str = "sa"
    sqlserver_password: str = ""
    sqlserver_driver: str = "ODBC Driver 17 for SQL Server"
    
    # MySQL Configuration
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "capstoneexam"
    mysql_username: str = "root"
    mysql_password: str = ""
    
    # PostgreSQL Configuration
    postgresql_host: str = "localhost"
    postgresql_port: int = 5432
    postgresql_database: str = "capstoneexam"
    postgresql_username: str = "postgres"
    postgresql_password: str = ""
    
    # MongoDB Configuration
    mongodb_host: str = "localhost"
    mongodb_port: int = 27017
    mongodb_database: str = "capstoneexam"
    mongodb_username: Optional[str] = None
    mongodb_password: Optional[str] = None
    
    # Application Configuration
    app_name: str = "CapstoneExam API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings