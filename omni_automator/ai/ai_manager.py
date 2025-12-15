#!/usr/bin/env python3
"""
Modular AI System with Model Switching Capabilities
Supports multiple AI backends: OpenRouter, local models, fallback
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum


@dataclass
class AIConfig:
    """AI Configuration"""
    provider: str  # openrouter, local, fallback
    model: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    enable_fallback: bool = True


class AIProvider(Enum):
    """Available AI providers"""
    OPENROUTER = "openrouter"
    LOCAL = "local"
    FALLBACK = "fallback"


class AIModel(Enum):
    """Available AI models"""
    # OpenRouter Models
    GPT4 = "openai/gpt-4-turbo"
    GPT35 = "openai/gpt-3.5-turbo"
    CLAUDE_3_OPUS = "anthropic/claude-3-opus"
    CLAUDE_3_SONNET = "anthropic/claude-3-sonnet"
    GEMINI_PRO = "google/gemini-pro-1.5"
    
    # Local Models
    OLLAMA_MISTRAL = "mistral"
    OLLAMA_LLAMA2 = "llama2"
    
    # Fallback
    REGEX_PARSER = "regex"


@dataclass
class AIResponse:
    """Structured AI response"""
    success: bool
    content: str
    model_used: str
    provider: str
    tokens_used: Optional[int] = None
    execution_plan: Optional[Dict[str, Any]] = None
    confidence: float = 0.5


class AIBackend(ABC):
    """Abstract base class for AI backends"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available"""
        pass
    
    @abstractmethod
    def query(self, prompt: str, **kwargs) -> AIResponse:
        """Query the AI backend"""
        pass


class OpenRouterBackend(AIBackend):
    """OpenRouter AI backend"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.logger = logging.getLogger("OpenRouterBackend")
        self._available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize OpenRouter connection"""
        try:
            import openai
            if not self.config.api_key:
                self.config.api_key = os.getenv('OPENROUTER_API_KEY')
            
            if not self.config.api_key:
                self.logger.warning("No OpenRouter API key provided")
                return
            
            openai.api_key = self.config.api_key
            openai.api_base = "https://openrouter.ai/api/v1"
            self._available = True
            self.logger.info(f"OpenRouter initialized with model: {self.config.model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenRouter: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        """Check if OpenRouter is available"""
        return self._available
    
    def query(self, prompt: str, **kwargs) -> AIResponse:
        """Query OpenRouter API"""
        if not self.is_available():
            return AIResponse(
                success=False,
                content="OpenRouter not available",
                model_used=self.config.model,
                provider=AIProvider.OPENROUTER.value,
                confidence=0.0
            )
        
        try:
            import openai
            response = openai.ChatCompletion.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            return AIResponse(
                success=True,
                content=response.choices[0].message.content,
                model_used=self.config.model,
                provider=AIProvider.OPENROUTER.value,
                tokens_used=response.usage.total_tokens,
                confidence=0.95
            )
        except Exception as e:
            self.logger.error(f"OpenRouter query failed: {e}")
            return AIResponse(
                success=False,
                content=str(e),
                model_used=self.config.model,
                provider=AIProvider.OPENROUTER.value,
                confidence=0.0
            )


class LocalBackend(AIBackend):
    """Local AI backend (Ollama)"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.logger = logging.getLogger("LocalBackend")
        self._available = self._check_ollama()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if local backend is available"""
        return self._available
    
    def query(self, prompt: str, **kwargs) -> AIResponse:
        """Query local model via Ollama"""
        if not self.is_available():
            return AIResponse(
                success=False,
                content="Local backend (Ollama) not available",
                model_used=self.config.model,
                provider=AIProvider.LOCAL.value,
                confidence=0.0
            )
        
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": self.config.temperature
                },
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return AIResponse(
                    success=True,
                    content=result.get("response", ""),
                    model_used=self.config.model,
                    provider=AIProvider.LOCAL.value,
                    confidence=0.85
                )
            else:
                return AIResponse(
                    success=False,
                    content=f"API error: {response.status_code}",
                    model_used=self.config.model,
                    provider=AIProvider.LOCAL.value,
                    confidence=0.0
                )
        except Exception as e:
            self.logger.error(f"Local query failed: {e}")
            return AIResponse(
                success=False,
                content=str(e),
                model_used=self.config.model,
                provider=AIProvider.LOCAL.value,
                confidence=0.0
            )


class FallbackBackend(AIBackend):
    """Fallback backend (regex-based parser)"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.logger = logging.getLogger("FallbackBackend")
    
    def is_available(self) -> bool:
        """Fallback is always available"""
        return True
    
    def query(self, prompt: str, **kwargs) -> AIResponse:
        """Use fallback parser"""
        # This would use the existing regex-based command parser
        return AIResponse(
            success=True,
            content=f"Using fallback parser for: {prompt}",
            model_used=self.config.model,
            provider=AIProvider.FALLBACK.value,
            confidence=0.5
        )


class AIManager:
    """Manager for switching between different AI backends"""
    
    def __init__(self, config: Optional[AIConfig] = None):
        """Initialize AI Manager with configuration"""
        self.logger = logging.getLogger("AIManager")
        
        if config is None:
            config = self._get_default_config()
        
        self.config = config
        self.backends: Dict[AIProvider, AIBackend] = {}
        self.current_provider = AIProvider.FALLBACK
        
        self._initialize_backends()
        self._select_best_available_backend()
    
    def _get_default_config(self) -> AIConfig:
        """Get default configuration"""
        return AIConfig(
            provider="openrouter",
            model="google/gemini-pro-1.5",
            api_key=os.getenv('OPENROUTER_API_KEY'),
            temperature=0.7,
            max_tokens=2048
        )
    
    def _initialize_backends(self):
        """Initialize all available backends"""
        # Initialize OpenRouter
        self.backends[AIProvider.OPENROUTER] = OpenRouterBackend(self.config)
        
        # Initialize Local
        local_config = AIConfig(
            provider="local",
            model=self.config.model.split('/')[-1] if '/' in self.config.model else self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        self.backends[AIProvider.LOCAL] = LocalBackend(local_config)
        
        # Initialize Fallback (always available)
        fallback_config = AIConfig(
            provider="fallback",
            model="regex",
            temperature=0.5,
            max_tokens=1024
        )
        self.backends[AIProvider.FALLBACK] = FallbackBackend(fallback_config)
    
    def _select_best_available_backend(self):
        """Select the best available backend"""
        # Try in order of preference
        preference_order = [
            AIProvider.OPENROUTER,
            AIProvider.LOCAL,
            AIProvider.FALLBACK
        ]
        
        for provider in preference_order:
            if self.backends[provider].is_available():
                self.current_provider = provider
                self.logger.info(f"Selected AI provider: {provider.value}")
                return
        
        self.logger.warning("No AI providers available, using fallback")
        self.current_provider = AIProvider.FALLBACK
    
    def switch_provider(self, provider: AIProvider) -> bool:
        """Switch to a different AI provider"""
        if provider not in self.backends:
            self.logger.error(f"Provider {provider.value} not initialized")
            return False
        
        if not self.backends[provider].is_available():
            self.logger.error(f"Provider {provider.value} is not available")
            return False
        
        self.current_provider = provider
        self.logger.info(f"Switched to provider: {provider.value}")
        return True
    
    def switch_model(self, model: str, provider: Optional[AIProvider] = None) -> bool:
        """Switch to a different model"""
        if provider is None:
            provider = self.current_provider
        
        if provider not in self.backends:
            self.logger.error(f"Provider {provider.value} not found")
            return False
        
        # Update configuration
        self.config.model = model
        
        # Re-initialize the backend with new model
        if provider == AIProvider.OPENROUTER:
            config = AIConfig(
                provider="openrouter",
                model=model,
                api_key=self.config.api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            self.backends[provider] = OpenRouterBackend(config)
        
        self.logger.info(f"Switched to model: {model}")
        return True
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [
            provider.value 
            for provider, backend in self.backends.items() 
            if backend.is_available()
        ]
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        models = [model.value for model in AIModel]
        return models
    
    def query(self, prompt: str, **kwargs) -> AIResponse:
        """Query the current AI backend"""
        backend = self.backends[self.current_provider]
        
        response = backend.query(prompt, **kwargs)
        
        # If query failed and fallback is enabled, try fallback
        if not response.success and self.config.enable_fallback and self.current_provider != AIProvider.FALLBACK:
            self.logger.warning(f"Query failed with {self.current_provider.value}, falling back")
            fallback = self.backends[AIProvider.FALLBACK]
            response = fallback.query(prompt, **kwargs)
        
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI system status"""
        return {
            'current_provider': self.current_provider.value,
            'available_providers': self.get_available_providers(),
            'model': self.config.model,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'backends_status': {
                provider.value: backend.is_available()
                for provider, backend in self.backends.items()
            }
        }


# Singleton instance
_ai_manager_instance: Optional[AIManager] = None


def get_ai_manager(config: Optional[AIConfig] = None) -> AIManager:
    """Get or create AI Manager singleton"""
    global _ai_manager_instance
    
    if _ai_manager_instance is None:
        _ai_manager_instance = AIManager(config)
    
    return _ai_manager_instance


def reset_ai_manager():
    """Reset AI Manager instance"""
    global _ai_manager_instance
    _ai_manager_instance = None
