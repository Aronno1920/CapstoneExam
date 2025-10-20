"""
Configuration settings for the AI Examiner System
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # GitHub Models Configuration
    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    github_endpoint: str = Field("https://models.github.ai/inference", env="GITHUB_ENDPOINT")
    github_model: str = Field("openai/gpt-4.1-nano", env="GITHUB_MODEL")
        
    llm_provider: str = Field("github", env="LLM_PROVIDER")
    llm_model: str = Field("openai/gpt-4.1-nano", env="LLM_MODEL")
    
    # Database Configuration
    database_url: str = Field("mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server", env="DATABASE_URL")
    db_server: str = Field("localhost", env="DB_SERVER")
    db_port: str = Field("1433", env="DB_PORT")
    db_name: str = Field("AIExaminerDB", env="DB_NAME")
    db_username: str = Field("sa", env="DB_USERNAME")
    db_password: str = Field("abc@123", env="DB_PASSWORD")
    db_driver: str = Field("ODBC Driver 17 for SQL Server", env="DB_DRIVER")
    use_windows_auth: bool = Field(True, env="USE_WINDOWS_AUTH")
    
    # Application Settings
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    max_answer_length: int = Field(2000, env="MAX_ANSWER_LENGTH")
    default_max_score: float = Field(100.0, env="DEFAULT_MAX_SCORE")
    
    # Grading Parameters
    min_similarity_threshold: float = Field(0.6, env="MIN_SIMILARITY_THRESHOLD")
    concept_extraction_temperature: float = Field(0.1, env="CONCEPT_EXTRACTION_TEMPERATURE")
    grading_temperature: float = Field(0.2, env="GRADING_TEMPERATURE")
    max_retries: int = Field(3, env="MAX_RETRIES")
    
    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_reload: bool = Field(True, env="API_RELOAD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in environment


# Global settings instance
settings = Settings()


# LLM Model configurations
LLM_CONFIGS = {
    # GitHub Models
    "openai/gpt-5-nano": {
        "provider": "github",
        "max_tokens": 4000,
        "temperature": 0.2,
        "supports_json_mode": True
    },
    "openai/gpt-4o-mini": {
        "provider": "github",
        "max_tokens": 4000,
        "temperature": 0.2,
        "supports_json_mode": True
    }
}


def get_llm_config(model_name: str) -> dict:
    """Get configuration for a specific LLM model"""
    if model_name in LLM_CONFIGS:
        return LLM_CONFIGS[model_name]
    # Fallback to GitHub default model
    return LLM_CONFIGS["openai/gpt-5-nano"]


def validate_api_keys() -> dict:
    """Validate that required API keys are available"""
    validation_result = {
        "github": bool(settings.github_token),
        "selected_provider_valid": False
    }
    
    if settings.llm_provider == "github":
        validation_result["selected_provider_valid"] = validation_result["github"]
    
    return validation_result
