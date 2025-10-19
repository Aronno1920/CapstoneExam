"""
Configuration settings for the AI Examiner System
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Configuration
    
    # GitHub Models Configuration
    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    github_endpoint: str = Field("https://models.github.ai/inference", env="GITHUB_ENDPOINT")
    github_model: str = Field("openai/gpt-4.1-nano", env="GITHUB_MODEL")
    
    llm_provider: str = Field("openai", env="LLM_PROVIDER")
    llm_model: str = Field("gpt-4", env="LLM_MODEL")
    
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


# Prompt templates for LLM interactions
class PromptTemplates:
    """Collection of prompt templates for different LLM tasks"""
    
    CONCEPT_EXTRACTION = """
      You are an expert academic examiner analyzing an ideal answer to extract key concepts.

      IDEAL ANSWER:
      {ideal_answer}

      SUBJECT: {subject}
      TOPIC: {topic}

      TASK: Extract 3-7 key concepts from this ideal answer. For each concept:
      1. Identify the core idea or principle
      2. Rate its importance (0.0-1.0) based on how central it is to answering the question
      3. List 2-4 relevant keywords
      4. Provide a clear explanation

      OUTPUT FORMAT (JSON):
      {{
        "key_concepts": [
          {{
            "concept": "Brief concept name",
            "importance": 0.8,
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "explanation": "Detailed explanation of this concept"
          }}
        ]
      }}

      Ensure concepts are distinct, non-overlapping, and capture the essential elements needed for a complete answer.
      """

    SEMANTIC_ANALYSIS = """
      You are an expert academic examiner performing semantic analysis of a student answer.

      IDEAL ANSWER:
      {ideal_answer}

      STUDENT ANSWER:
      {student_answer}

      KEY CONCEPTS TO EVALUATE:
      {key_concepts}

      TASK: Analyze the student answer for each key concept. Determine:
      1. Is the concept present in the student answer?
      2. How accurately is it explained? (0.0-1.0 accuracy score)
      3. Provide evidence from the student answer
      4. Explain your evaluation

      OUTPUT FORMAT (JSON):
      {{
        "concept_evaluations": [
          {{
            "concept": "Concept name",
            "present": true/false,
            "accuracy_score": 0.8,
            "explanation": "Detailed explanation of evaluation",
            "evidence": "Quote from student answer or null if not present"
          }}
        ],
        "overall_semantic_similarity": 0.75,
        "coherence_score": 0.8,
        "completeness_score": 0.7
      }}

      Be objective and precise in your evaluation. Consider partial credit for concepts that are mentioned but not fully explained.
      """

    GRADING_RUBRIC_APPLICATION = """
      You are an expert academic examiner applying a grading rubric to evaluate a student answer.

      IDEAL ANSWER:
      {ideal_answer}

      STUDENT ANSWER:
      {student_answer}

      GRADING RUBRIC:
      {rubric}

      CONCEPT EVALUATIONS:
      {concept_evaluations}

      SEMANTIC ANALYSIS:
      - Semantic Similarity: {semantic_similarity}
      - Coherence Score: {coherence_score}
      - Completeness Score: {completeness_score}

      TASK: Apply the grading rubric to calculate scores and provide comprehensive feedback.

      PROCESS:
      1. For each grading criterion, evaluate how well the student answer meets it
      2. Assign points based on the rubric and concept evaluations
      3. Calculate total score and percentage
      4. Identify strengths, weaknesses, and suggestions
      5. Provide detailed feedback

      OUTPUT FORMAT (JSON):
      {{
        "criteria_scores": {{
          "criterion_name": score_value
        }},
        "total_score": calculated_total,
        "percentage": percentage_score,
        "passed": true/false,
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "suggestions": ["suggestion1", "suggestion2"],
        "detailed_feedback": "Comprehensive paragraph explaining the grade",
        "confidence_score": 0.85
      }}

      Be fair, constructive, and provide actionable feedback to help the student improve.
      """

    CHAIN_OF_THOUGHT_GRADING = """
      You are an expert academic examiner with years of experience in evaluating student answers. Your task is to grade a student's narrative answer by comparing it to an ideal answer using a structured approach.

      ROLE: Expert Academic Examiner specializing in {subject}

      IDEAL ANSWER:
      {ideal_answer}

      STUDENT ANSWER:
      {student_answer}

      GRADING RUBRIC:
      {rubric}

      PROCESS - Follow these steps carefully:

      Step 1: SEMANTIC UNDERSTANDING
      - Break down the ideal answer into 3-5 key concepts
      - For each concept, note its importance and required depth of understanding
      - List the essential elements that demonstrate mastery

      Step 2: STUDENT ANSWER ANALYSIS
      - Identify which key concepts the student addressed
      - Evaluate the accuracy and depth of each concept explanation
      - Note the overall coherence and structure of the response

      Step 3: CONCEPT-BY-CONCEPT COMPARISON
      - For each key concept from the ideal answer:
        * Is it present in the student answer? (Yes/No)
        * How accurately is it explained? (0-100%)
        * What evidence supports this evaluation?
        * Assign partial credit where appropriate

      Step 4: RUBRIC APPLICATION
      - Apply each grading criterion from the rubric
      - Calculate points for each criterion based on concept coverage
      - Consider factors like clarity, completeness, and understanding

      Step 5: FINAL EVALUATION
      - Sum the points and calculate percentage
      - Determine if the answer meets the passing threshold
      - Provide constructive feedback with specific examples

      OUTPUT FORMAT (JSON):
      {{
        "step1_key_concepts": [
          {{
            "concept": "concept name",
            "importance": 0.8,
            "required_depth": "explanation of what's needed"
          }}
        ],
        "step2_student_analysis": {{
          "concepts_addressed": ["concept1", "concept2"],
          "overall_coherence": 0.7,
          "structure_quality": 0.8
        }},
        "step3_concept_comparison": [
          {{
            "concept": "concept name",
            "present": true,
            "accuracy_percentage": 85,
            "evidence": "quote from student answer",
            "evaluation": "explanation of assessment"
          }}
        ],
        "step4_rubric_scores": {{
          "criterion_name": {{
            "points_awarded": 8.5,
            "max_points": 10,
            "justification": "explanation"
          }}
        }},
        "step5_final_result": {{
          "total_score": 85.5,
          "max_possible": 100,
          "percentage": 85.5,
          "passed": true,
          "overall_feedback": "Detailed feedback paragraph",
          "strengths": ["strength1", "strength2"],
          "areas_for_improvement": ["area1", "area2"],
          "specific_suggestions": ["suggestion1", "suggestion2"],
          "confidence_level": 0.9
        }}
      }}

      Remember: Be objective, fair, and provide constructive feedback that helps the student learn and improve.
      """


# LLM Model configurations
LLM_CONFIGS = {
    # GitHub Models
    "openai/gpt-4.1-nano": {
        "provider": "github",
        "max_tokens": 4000,
        "temperature": 0.2,
        "supports_json_mode": True
    },
    "openai/gpt-4o": {
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
    return LLM_CONFIGS.get(model_name, LLM_CONFIGS["gpt-4"])


def validate_api_keys() -> dict:
    """Validate that required API keys are available"""
    validation_result = {
        "github": bool(settings.github_token),
        "selected_provider_valid": False
    }
    
    if settings.llm_provider == "github":
        validation_result["selected_provider_valid"] = validation_result["github"]
    
    return validation_result
