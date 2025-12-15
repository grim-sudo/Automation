#!/usr/bin/env python3
"""
Modular AI System with Model Switching
Supports multiple AI providers and models
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import os
from datetime import datetime


@dataclass
class AIModelConfig:
    """Configuration for an AI model"""
    name: str
    provider: str  # 'openrouter', 'openai', 'anthropic', 'local'
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    is_default: bool = False


@dataclass
class AIResponse:
    """Response from AI model"""
    content: str
    model_used: str
    tokens_used: int
    provider: str
    timestamp: str
    task_plan: Optional[Dict[str, Any]] = None  # AI-generated execution plan


class AIModelProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def query(self, prompt: str, context: Dict[str, Any] = None) -> AIResponse:
        """Query the AI model"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that the provider is configured correctly"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass


class OpenRouterProvider(AIModelProvider):
    """OpenRouter AI provider"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.provider_name = "openrouter"
    
    def validate_config(self) -> bool:
        """Validate OpenRouter configuration"""
        if not self.config.api_key:
            return False
        
        if not self.config.model_id:
            return False
        
        return True
    
    def query(self, prompt: str, context: Dict[str, Any] = None) -> AIResponse:
        """Query OpenRouter API"""
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "HTTP-Referer": "https://omnimator.local",
                "X-Title": "OmniAutomator"
            }
            
            data = {
                "model": self.config.model_id,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }
            
            if context:
                data["messages"].insert(0, {
                    "role": "system",
                    "content": self._build_system_prompt(context)
                })
            
            response = requests.post(
                "https://openrouter.io/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return AIResponse(
                    content=result['choices'][0]['message']['content'],
                    model_used=self.config.model_id,
                    tokens_used=result.get('usage', {}).get('total_tokens', 0),
                    provider=self.provider_name,
                    timestamp=datetime.now().isoformat()
                )
            else:
                return AIResponse(
                    content=f"Error: {response.status_code}",
                    model_used=self.config.model_id,
                    tokens_used=0,
                    provider=self.provider_name,
                    timestamp=datetime.now().isoformat()
                )
        
        except Exception as e:
            return AIResponse(
                content=f"Error querying OpenRouter: {str(e)}",
                model_used=self.config.model_id,
                tokens_used=0,
                provider=self.provider_name,
                timestamp=datetime.now().isoformat()
            )
    
    def get_available_models(self) -> List[str]:
        """Get available models from OpenRouter"""
        return [
            "openai/gpt-4",
            "openai/gpt-4-turbo",
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet",
            "google/palm-2",
            "meta-llama/llama-2-70b",
        ]
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt from context"""
        prompt = "You are OmniAutomator, an intelligent automation assistant.\n\n"
        
        if 'task' in context:
            prompt += f"Current Task: {context['task']}\n"
        
        if 'capabilities' in context:
            prompt += f"Available Capabilities: {', '.join(context['capabilities'])}\n"
        
        if 'constraints' in context:
            prompt += f"Constraints: {', '.join(context['constraints'])}\n"
        
        return prompt


class LocalProvider(AIModelProvider):
    """Local AI provider (for testing/offline)"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.provider_name = "local"
    
    def validate_config(self) -> bool:
        """Validate local configuration"""
        return True  # Local provider always available
    
    def query(self, prompt: str, context: Dict[str, Any] = None) -> AIResponse:
        """Simple local response (for testing)"""
        # This would integrate with Ollama or other local LLM
        response = self._generate_local_response(prompt, context)
        
        return AIResponse(
            content=response,
            model_used=self.config.model_id,
            tokens_used=len(prompt.split()),
            provider=self.provider_name,
            timestamp=datetime.now().isoformat()
        )
    
    def _generate_local_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response locally (stub)"""
        # In production, this would call Ollama, LLaMA.cpp, or similar
        return f"Local response: {prompt[:50]}..."
    
    def get_available_models(self) -> List[str]:
        """Get available local models"""
        return [
            "ollama/llama2",
            "ollama/mistral",
            "ollama/neural-chat",
        ]


class AIModelManager:
    """Manage multiple AI models and providers"""
    
    def __init__(self):
        self.models: Dict[str, AIModelConfig] = {}
        self.providers: Dict[str, AIModelProvider] = {}
        self.current_model: Optional[str] = None
        self.config_file = os.path.expanduser("~/.omnimator/ai_config.json")
        
        self._load_config()
    
    def register_model(self, config: AIModelConfig) -> bool:
        """Register a new AI model"""
        if not self._validate_model_config(config):
            return False
        
        self.models[config.name] = config
        
        # Create provider
        provider = self._create_provider(config)
        if provider and provider.validate_config():
            self.providers[config.name] = provider
        
        # Set as default if specified
        if config.is_default:
            self.current_model = config.name
        
        # Save configuration
        self._save_config()
        
        return True
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different AI model"""
        if model_name not in self.models:
            return False
        
        self.current_model = model_name
        self._save_config()
        
        return True
    
    def query(self, prompt: str, context: Dict[str, Any] = None, model: str = None) -> AIResponse:
        """Query AI with optional model specification"""
        target_model = model or self.current_model
        
        if not target_model or target_model not in self.providers:
            return AIResponse(
                content="No AI model configured",
                model_used="none",
                tokens_used=0,
                provider="none",
                timestamp=datetime.now().isoformat()
            )
        
        provider = self.providers[target_model]
        return provider.query(prompt, context)
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get all available models by provider"""
        available = {}
        
        for name, provider in self.providers.items():
            provider_name = provider.provider_name
            if provider_name not in available:
                available[provider_name] = []
            available[provider_name].extend(provider.get_available_models())
        
        return available
    
    def get_current_model_info(self) -> Optional[Dict[str, Any]]:
        """Get info about current model"""
        if not self.current_model or self.current_model not in self.models:
            return None
        
        config = self.models[self.current_model]
        
        return {
            'name': config.name,
            'provider': config.provider,
            'model_id': config.model_id,
            'max_tokens': config.max_tokens,
            'temperature': config.temperature
        }
    
    def list_registered_models(self) -> Dict[str, Dict[str, Any]]:
        """List all registered models"""
        return {
            name: {
                'provider': config.provider,
                'model_id': config.model_id,
                'is_current': name == self.current_model
            }
            for name, config in self.models.items()
        }
    
    def _create_provider(self, config: AIModelConfig) -> Optional[AIModelProvider]:
        """Create provider instance based on config"""
        if config.provider == 'openrouter':
            return OpenRouterProvider(config)
        elif config.provider == 'local':
            return LocalProvider(config)
        else:
            return None
    
    def _validate_model_config(self, config: AIModelConfig) -> bool:
        """Validate model configuration"""
        if not config.name or not config.provider or not config.model_id:
            return False
        
        if config.provider == 'openrouter' and not config.api_key:
            return False
        
        return True
    
    def _load_config(self):
        """Load AI configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                for model_data in data.get('models', []):
                    config = AIModelConfig(**model_data)
                    self.register_model(config)
                
                self.current_model = data.get('current_model')
            except Exception as e:
                print(f"Error loading AI config: {e}")
    
    def _save_config(self):
        """Save AI configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            data = {
                'models': [
                    {
                        'name': config.name,
                        'provider': config.provider,
                        'model_id': config.model_id,
                        'max_tokens': config.max_tokens,
                        'temperature': config.temperature,
                        'is_default': config.is_default
                    }
                    for config in self.models.values()
                ],
                'current_model': self.current_model,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving AI config: {e}")


# Singleton instance
_ai_manager = AIModelManager()


def get_ai_manager() -> AIModelManager:
    """Get AI model manager instance"""
    return _ai_manager
