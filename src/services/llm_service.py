"""
LLM Service for AI Examiner System
Handles interactions with different LLM providers (OpenAI, Anthropic)
"""
import json
import time
import logging
from typing import Dict, Any, Optional, Union, List
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import openai
from anthropic import Anthropic, APIError as AnthropicAPIError
from openai import OpenAI, APIError as OpenAIAPIError

from ..utils.config import settings, get_llm_config, PromptTemplates
from ..models.schemas import LLMProvider, LLMModel


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class LLMProviderError(LLMError):
    """Exception for LLM provider-specific errors"""
    pass


class LLMResponseParsingError(LLMError):
    """Exception for response parsing errors"""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.config = get_llm_config(model)
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate that the LLM connection is working"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation"""
    
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self.client = OpenAI(api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(OpenAIAPIError)
    )
    async def generate_response(
        self, 
        prompt: str, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """Generate response from OpenAI API"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.config["temperature"],
                "max_tokens": max_tokens or self.config["max_tokens"]
            }
            
            # Add JSON mode if supported and requested
            if json_mode and self.config.get("supports_json_mode", False):
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
            
        except OpenAIAPIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMProviderError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    def validate_connection(self) -> bool:
        """Validate OpenAI connection"""
        try:
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider implementation"""
    
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self.client = Anthropic(api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(AnthropicAPIError)
    )
    async def generate_response(
        self, 
        prompt: str, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """Generate response from Anthropic API"""
        try:
            # Add JSON instruction to prompt if JSON mode requested
            if json_mode:
                prompt += "\n\nIMPORTANT: Respond with valid JSON only, no additional text."
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.config["max_tokens"],
                temperature=temperature or self.config["temperature"],
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except AnthropicAPIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise LLMProviderError(f"Anthropic API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic provider: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    def validate_connection(self) -> bool:
        """Validate Anthropic connection"""
        try:
            # Simple test message to validate connection
            self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {e}")
            return False


class LLMService:
    """Main LLM service that manages different providers"""
    
    def __init__(self):
        self.provider: Optional[BaseLLMProvider] = None
        self.initialize_provider()
    
    def initialize_provider(self) -> None:
        """Initialize the appropriate LLM provider based on settings"""
        try:
            if settings.llm_provider == LLMProvider.OPENAI:
                if not settings.openai_api_key:
                    raise LLMError("OpenAI API key not configured")
                self.provider = OpenAIProvider(settings.openai_api_key, settings.llm_model)
            
            elif settings.llm_provider == LLMProvider.ANTHROPIC:
                if not settings.anthropic_api_key:
                    raise LLMError("Anthropic API key not configured")
                self.provider = AnthropicProvider(settings.anthropic_api_key, settings.llm_model)
            
            else:
                raise LLMError(f"Unsupported LLM provider: {settings.llm_provider}")
            
            logger.info(f"Initialized {settings.llm_provider} provider with model {settings.llm_model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            raise
    
    async def extract_key_concepts(self, ideal_answer: str, subject: str, topic: str) -> List[Dict[str, Any]]:
        """Extract key concepts from an ideal answer"""
        prompt = PromptTemplates.CONCEPT_EXTRACTION.format(
            ideal_answer=ideal_answer,
            subject=subject,
            topic=topic
        )
        
        try:
            response = await self.provider.generate_response(
                prompt=prompt,
                temperature=settings.concept_extraction_temperature,
                json_mode=True
            )
            
            # Parse JSON response
            parsed_response = self._parse_json_response(response)
            return parsed_response.get("key_concepts", [])
            
        except Exception as e:
            logger.error(f"Error extracting key concepts: {e}")
            raise LLMError(f"Failed to extract key concepts: {e}")
    
    async def analyze_semantic_similarity(
        self, 
        ideal_answer: str, 
        student_answer: str, 
        key_concepts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze semantic similarity between ideal and student answers"""
        key_concepts_str = json.dumps(key_concepts, indent=2)
        
        prompt = PromptTemplates.SEMANTIC_ANALYSIS.format(
            ideal_answer=ideal_answer,
            student_answer=student_answer,
            key_concepts=key_concepts_str
        )
        
        try:
            response = await self.provider.generate_response(
                prompt=prompt,
                temperature=settings.grading_temperature,
                json_mode=True
            )
            
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing semantic similarity: {e}")
            raise LLMError(f"Failed to analyze semantic similarity: {e}")
    
    async def apply_grading_rubric(
        self,
        ideal_answer: str,
        student_answer: str,
        rubric: Dict[str, Any],
        concept_evaluations: List[Dict[str, Any]],
        semantic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply grading rubric to calculate final score and feedback"""
        rubric_str = json.dumps(rubric, indent=2)
        concept_evaluations_str = json.dumps(concept_evaluations, indent=2)
        
        prompt = PromptTemplates.GRADING_RUBRIC_APPLICATION.format(
            ideal_answer=ideal_answer,
            student_answer=student_answer,
            rubric=rubric_str,
            concept_evaluations=concept_evaluations_str,
            semantic_similarity=semantic_analysis.get("overall_semantic_similarity", 0),
            coherence_score=semantic_analysis.get("coherence_score", 0),
            completeness_score=semantic_analysis.get("completeness_score", 0)
        )
        
        try:
            response = await self.provider.generate_response(
                prompt=prompt,
                temperature=settings.grading_temperature,
                json_mode=True
            )
            
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Error applying grading rubric: {e}")
            raise LLMError(f"Failed to apply grading rubric: {e}")
    
    async def chain_of_thought_grading(
        self,
        ideal_answer: str,
        student_answer: str,
        subject: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive Chain-of-Thought grading"""
        rubric_str = json.dumps(rubric, indent=2)
        
        prompt = PromptTemplates.CHAIN_OF_THOUGHT_GRADING.format(
            ideal_answer=ideal_answer,
            student_answer=student_answer,
            subject=subject,
            rubric=rubric_str
        )
        
        try:
            response = await self.provider.generate_response(
                prompt=prompt,
                temperature=settings.grading_temperature,
                json_mode=True
            )
            
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Error in chain-of-thought grading: {e}")
            raise LLMError(f"Failed to perform chain-of-thought grading: {e}")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response with error handling"""
        try:
            # Remove any potential markdown formatting
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            raise LLMResponseParsingError(f"Invalid JSON response: {e}")
    
    def validate_connection(self) -> bool:
        """Validate that the LLM service is properly configured and connected"""
        if not self.provider:
            return False
        
        return self.provider.validate_connection()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider and model"""
        return {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "config": get_llm_config(settings.llm_model),
            "connected": self.validate_connection() if self.provider else False
        }


# Global LLM service instance
llm_service = LLMService()