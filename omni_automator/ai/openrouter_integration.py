#!/usr/bin/env python3
"""
OpenRouter AI Integration for OmniAutomator
Supports multiple models: GPT-4, Claude, Gemini, and more
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Try to import OpenAI (OpenRouter uses OpenAI-compatible API)
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from ..utils.logger import get_logger

@dataclass
class AITaskPlan:
    """AI-generated task execution plan"""
    original_request: str
    interpreted_intent: str
    confidence_score: float
    execution_steps: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    optimization_suggestions: List[str]


class OpenRouterAutomationAI:
    """OpenRouter AI integration for intelligent automation with multiple model support"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistralai/devstral-2512:free"):
        self.logger = get_logger("OpenRouterAI")
        
        # Validate inputs
        if api_key is not None and not isinstance(api_key, str):
            raise ValueError("API key must be a string")
        if not isinstance(model, str):
            raise ValueError("Model name must be a string")
        
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.client = None
        self.model_name = model  # Default to DevStral (best free model)
        self.is_available = False
        self.last_error = None
        
        # Available models on OpenRouter
        self.available_models = {
            "openai/gpt-4o": "GPT-4o (Most Capable)",
            "openai/gpt-4o-mini": "GPT-4o Mini (Fast & Cheap)",
            "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet",
            "google/gemini-pro-1.5": "Gemini Pro 1.5",
            "meta-llama/llama-3.1-8b-instruct": "Llama 3.1 8B",
            "deepseek/deepseek-r1": "DeepSeek R1",
            "kwaipilot/kat-coder-pro:free": "KAT Coder Pro",
            "tngtech/deepseek-r1t2-chimera:free": "DeepSeek R1T2 Chimera",
            "mistralai/devstral-2512:free": "DevStral 2512 (Best Balance)",
            "google/gemini-2.0-flash-exp:free": "Gemini 2.0 Flash Exp"
        }
        
        # Validate model name - default to DevStral if not found
        if self.model_name not in self.available_models:
            self.logger.warning(f"Unknown model: {self.model_name}. Using DevStral-2512.")
            self.model_name = "mistralai/devstral-2512:free"
        
        # System context for automation
        self.system_context = self._build_system_context()
        
        # Initialize OpenRouter if available
        self._initialize_openrouter()
    
    def _initialize_openrouter(self):
        """Initialize OpenRouter AI client"""
        try:
            if not HAS_OPENAI:
                self.last_error = "OpenAI library not available"
                self.logger.warning("OpenAI library not available. Install with: pip install openai")
                return
            
            if not self.api_key:
                self.last_error = "API key not provided"
                self.logger.warning("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable")
                return
            
            # Validate API key format
            if not self.api_key.startswith('sk-or-v1-'):
                self.last_error = "Invalid API key format"
                self.logger.warning("OpenRouter API key should start with 'sk-or-v1-'")
                return
            
            # OpenRouter uses OpenAI-compatible API
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=30.0  # Add timeout
            )
            
            # Test the connection with a minimal request
            test_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                timeout=10.0,
                extra_headers={
                    "HTTP-Referer": "https://omni-automator.local",
                    "X-Title": "OmniAutomator"
                }
            )
            
            if test_response and test_response.choices:
                self.is_available = True
                self.last_error = None
                self.logger.info(f"✅ OpenRouter AI initialized successfully with: {self.model_name}")
            else:
                self.last_error = "Invalid response from API"
                self.logger.error("Invalid response from OpenRouter API")
            
        except openai.AuthenticationError as e:
            self.last_error = f"Authentication failed: {e}"
            self.logger.error(f"OpenRouter authentication failed: {e}")
        except openai.RateLimitError as e:
            self.last_error = f"Rate limit exceeded: {e}"
            self.logger.error(f"OpenRouter rate limit exceeded: {e}")
        except openai.APIConnectionError as e:
            self.last_error = f"Connection failed: {e}"
            self.logger.error(f"Failed to connect to OpenRouter: {e}")
        except Exception as e:
            self.last_error = f"Initialization failed: {e}"
            self.logger.error(f"Failed to initialize OpenRouter AI: {e}")
    
    def _build_system_context(self) -> str:
        """Build system context for OpenRouter AI"""
        return """
You are an AI assistant integrated into OmniAutomator, a universal OS automation framework. Your role is to:

1. INTERPRET natural language automation requests intelligently
2. ANALYZE user intent and break down complex tasks
3. GENERATE structured execution plans with proper steps
4. ASSESS risks and suggest safety measures
5. OPTIMIZE workflows for efficiency and reliability

CAPABILITIES YOU CAN LEVERAGE:
- File system operations (create, move, copy, delete files/folders) - use category: "filesystem"
- Process management (start/stop applications, manage services) - use category: "process"
- GUI automation (click, type, screenshot, window management) - use category: "gui"
- Network operations (download files, API calls, web scraping) - use category: "network"
- System information gathering - use category: "system"
- Development environment setup - use category: "project_generator"
- Project generation and scaffolding - use category: "project_generator"
- Package installation and dependency management - use category: "package_manager"

RESPONSE FORMAT:
Always respond with valid JSON containing:
{
    "intent": "Clear description of what user wants to accomplish",
    "confidence": 0.85,
    "steps": [
        {
            "action": "specific_action_name",
            "category": "action_category",
            "params": {"key": "value"},
            "description": "Human readable description"
        }
    ],
    "risks": {
        "level": "low|medium|high|critical",
        "concerns": ["list of potential issues"],
        "mitigations": ["suggested safety measures"]
    },
    "optimizations": ["suggestions for better execution"]
}

IMPORTANT CATEGORY MAPPINGS:
- For file/folder operations: use "filesystem" (NOT "file_system")
- For creating folders: {"action": "create_folder", "category": "filesystem", "params": {"name": "folder_name", "location": "path"}}
- For creating files: {"action": "create_file", "category": "filesystem", "params": {"name": "file_name", "location": "path", "content": "file_content"}}
- For process operations: use "process"
- For GUI operations: use "gui"
- For network operations: use "network"
- For system operations: use "system"

SAFETY RULES:
- Never suggest destructive operations on system files
- Always recommend backups before major changes
- Suggest sandbox mode for testing
- Flag high-risk operations clearly
- Prioritize user data safety
"""
    
    def analyze_automation_request(self, user_request: str, context: Dict[str, Any] = None) -> AITaskPlan:
        """Analyze user request and generate intelligent task plan"""
        
        if not self.is_available:
            return self._fallback_analysis(user_request)
        
        try:
            # Build prompt with context
            prompt = self._build_analysis_prompt(user_request, context or {})
            
            # Get AI response
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_context},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.3,
                extra_headers={
                    "HTTP-Referer": "https://omni-automator.local",
                    "X-Title": "OmniAutomator"
                }
            )
            
            # Parse AI response
            ai_analysis = self._parse_ai_response(response.choices[0].message.content)
            
            # Create task plan
            task_plan = AITaskPlan(
                original_request=user_request,
                interpreted_intent=ai_analysis.get('intent', user_request),
                confidence_score=ai_analysis.get('confidence', 0.5),
                execution_steps=ai_analysis.get('steps', []),
                risk_assessment=ai_analysis.get('risks', {'level': 'medium', 'concerns': [], 'mitigations': []}),
                optimization_suggestions=ai_analysis.get('optimizations', [])
            )
            
            return task_plan
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return self._fallback_analysis(user_request)
    
    def _build_analysis_prompt(self, request: str, context: Dict[str, Any]) -> str:
        """Build analysis prompt with context"""
        
        context_info = []
        if context.get('os_type'):
            context_info.append(f"Operating System: {context['os_type']}")
        if context.get('current_directory'):
            context_info.append(f"Current Directory: {context['current_directory']}")
        if context.get('recent_commands'):
            context_info.append(f"Recent Commands: {', '.join(context['recent_commands'][-3:])}")
        
        context_str = "\n".join(context_info) if context_info else "No additional context"
        
        return f"""
AUTOMATION REQUEST: {request}

CONTEXT:
{context_str}

Please analyze this automation request and provide a structured response in JSON format as specified in the system context.
Focus on breaking down the request into actionable steps that the OmniAutomator can execute.
"""
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into structured data with robust error handling"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Handle empty response
            if not response_text:
                self.logger.warning("Empty AI response received")
                return self._get_fallback_response()
            
            # Find JSON block
            json_text = None
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                json_text = response_text[start:end].strip()
            elif response_text.startswith('{'):
                json_text = response_text
            else:
                # Try to find JSON-like content
                start = response_text.find('{')
                end = response_text.rfind('}')
                if start >= 0 and end > start:
                    json_text = response_text[start:end+1]
            
            # Validate JSON
            if not json_text or not json_text.strip():
                self.logger.warning("Empty JSON content in AI response")
                return self._extract_intent_from_text(response_text)
            
            # Try to parse JSON - with error recovery
            try:
                parsed = json.loads(json_text)
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                self.logger.warning(f"JSON decode error (attempting recovery): {json_err}")
                
                # Fix unterminated strings by closing them
                if 'Unterminated string' in str(json_err):
                    json_text = self._fix_unterminated_strings(json_text)
                    try:
                        parsed = json.loads(json_text)
                    except:
                        return self._extract_intent_from_text(response_text)
                else:
                    return self._extract_intent_from_text(response_text)
            
            # Validate required fields
            if not isinstance(parsed, dict):
                self.logger.warning("AI response is not a dictionary")
                return self._get_fallback_response()
            
            return parsed
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON decode error in AI response: {e}")
            return self._get_fallback_response()
        except Exception as e:
            self.logger.warning(f"Failed to parse AI response: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> Dict[str, Any]:
        """Get fallback response when AI parsing fails"""
        return {
            "intent": "Basic command execution",
            "confidence": 0.3,
            "steps": [],
            "risks": {"level": "medium", "concerns": [], "mitigations": []},
            "optimizations": ["Enable AI for better analysis"]
        }
    
    def _fix_unterminated_strings(self, json_text: str) -> str:
        """Attempt to fix unterminated strings in JSON"""
        try:
            # Simple approach: fix common unterminated string patterns
            lines = json_text.split('\n')
            fixed_lines = []
            
            for line in lines:
                # Count quotes in the line (excluding escaped quotes)
                quote_count = line.count('"') - line.count('\\"')
                
                # If odd number of quotes, add closing quote before comma/bracket
                if quote_count % 2 == 1:
                    line = line.rstrip()
                    # Find where to insert the quote
                    if line.endswith(',') or line.endswith('}') or line.endswith(']'):
                        line = line[:-1] + '"' + line[-1]
                    else:
                        line = line + '"'
                
                fixed_lines.append(line)
            
            return '\n'.join(fixed_lines)
        except:
            return json_text
    
    def _extract_intent_from_text(self, response_text: str) -> Dict[str, Any]:
        """Extract intent from text when JSON parsing fails"""
        # Look for keywords to determine intent
        text_lower = response_text.lower()
        
        if 'create' in text_lower or 'setup' in text_lower:
            intent = 'Create project structure'
        elif 'install' in text_lower or 'deploy' in text_lower:
            intent = 'Install and deploy'
        elif 'configure' in text_lower:
            intent = 'Configure system'
        else:
            intent = f'Analysis: {response_text[:80]}...'
        
        return {
            "intent": intent,
            "confidence": 0.5,
            "steps": [],
            "risks": {"level": "medium", "concerns": [], "mitigations": []},
            "optimizations": []
        }
    
    def _extract_basic_intent(self, response_text: str) -> Dict[str, Any]:
        """Extract basic intent when JSON parsing fails"""
        return {
            "intent": f"Basic interpretation: {response_text[:100]}...",
            "confidence": 0.3,
            "steps": [],
            "risks": {"level": "medium", "concerns": [], "mitigations": []},
            "optimizations": []
        }
    
    def _fallback_analysis(self, user_request: str) -> AITaskPlan:
        """Fallback analysis when AI is not available"""
        return AITaskPlan(
            original_request=user_request,
            interpreted_intent=f"Basic interpretation: {user_request}",
            confidence_score=0.2,
            execution_steps=[],
            risk_assessment={"level": "unknown", "concerns": ["AI analysis unavailable"], "mitigations": ["Manual review recommended"]},
            optimization_suggestions=["Enable AI for better analysis"]
        )
    
    def generate_smart_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Generate smart automation suggestions based on context"""
        
        if not self.is_available:
            return ["Try 'examples' for command ideas"]
        
        try:
            prompt = f"""
Based on the following context, suggest 5-8 useful automation commands that would be helpful:

CONTEXT:
- OS: {context.get('os_type', 'Unknown')}
- Recent commands: {context.get('recent_commands', [])}
- Current directory: {context.get('current_directory', 'Unknown')}

Provide practical, actionable suggestions that demonstrate OmniAutomator's capabilities.
Format as a simple list, one suggestion per line.
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful automation assistant. Provide practical command suggestions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
                extra_headers={
                    "HTTP-Referer": "https://omni-automator.local",
                    "X-Title": "OmniAutomator"
                }
            )
            
            suggestions_text = response.choices[0].message.content
            suggestions = [line.strip() for line in suggestions_text.split('\n') if line.strip() and not line.startswith('#')]
            
            return suggestions[:8]  # Limit to 8 suggestions
            
        except Exception as e:
            self.logger.error(f"Smart suggestions failed: {e}")
            return [
                "create folder 'MyProject'",
                "take screenshot",
                "get system info",
                "create a Python project with basic structure"
            ]
    
    def enhance_command_understanding(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhance command understanding with AI insights"""
        
        if not self.is_available:
            return {"enhanced": False, "original": command}
        
        try:
            prompt = f"""
Analyze this automation command and enhance it with better understanding:

COMMAND: {command}
CONTEXT: {context or {}}

Provide insights about:
1. What the user likely wants to accomplish
2. Any ambiguities that need clarification
3. Suggested improvements or alternatives
4. Potential issues or considerations

Respond in JSON format:
{{
    "enhanced_understanding": "clearer description",
    "suggestions": ["list of improvements"],
    "clarifications_needed": ["list of questions"],
    "confidence": 0.85
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert at understanding automation commands."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                extra_headers={
                    "HTTP-Referer": "https://omni-automator.local",
                    "X-Title": "OmniAutomator"
                }
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON
            try:
                if '```json' in response_text:
                    start = response_text.find('```json') + 7
                    end = response_text.find('```', start)
                    json_text = response_text[start:end].strip()
                elif response_text.startswith('{'):
                    json_text = response_text
                else:
                    # Find JSON-like content
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start >= 0 and end > start:
                        json_text = response_text[start:end]
                    else:
                        raise ValueError("No JSON found in response")
                
                result = json.loads(json_text)
                result["enhanced"] = True
                result["original"] = command
                return result
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                self.logger.warning(f"Failed to parse enhancement response: {parse_error}")
                return {
                    "enhanced": False, 
                    "original": command,
                    "enhanced_command": command,
                    "suggestions": [],
                    "confidence": 0.5
                }
            
        except Exception as e:
            self.logger.error(f"Command enhancement failed: {e}")
            return {
                "enhanced": False, 
                "original": command,
                "enhanced_command": command,
                "error": str(e)
            }
    
    def set_model(self, model_name: str) -> bool:
        """Switch to a different model"""
        if model_name in self.available_models:
            self.model_name = model_name
            self.logger.info(f"Switched to model: {model_name}")
            return True
        else:
            self.logger.error(f"Model {model_name} not available")
            return False
    
    def get_available_models(self) -> Dict[str, str]:
        """Get list of available models"""
        return self.available_models
    
    def is_openrouter_available(self) -> bool:
        """Check if OpenRouter AI is available and configured"""
        return self.is_available
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI integration status"""
        return {
            "available": self.is_available,
            "has_api_key": bool(self.api_key),
            "has_library": HAS_OPENAI,
            "model": self.model_name if self.is_available else None,
            "provider": "OpenRouter",
            "available_models": list(self.available_models.keys()) if self.is_available else []
        }
    
    def get_current_model(self) -> str:
        """Get the currently active model name"""
        return self.model_name if self.is_available else "None"
    
    def suggest_error_resolution(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest solutions for execution errors"""
        if not self.is_available:
            return {
                'suggestions': ['Check logs and try again', 'Enable AI for better error analysis'],
                'confidence': 0.1
            }
        
        try:
            error_prompt = f"""
An automation command failed with the following error:

ERROR: {error_info.get('error_message', 'Unknown error')}
COMMAND: {error_info.get('command', 'Unknown command')}
ERROR TYPE: {error_info.get('error_type', 'Unknown')}

Please suggest 3-5 specific solutions to fix this error. Focus on practical, actionable steps.
Respond with a simple list of suggestions, one per line.
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert at troubleshooting automation errors. Provide clear, actionable solutions."},
                    {"role": "user", "content": error_prompt}
                ],
                max_tokens=400,
                temperature=0.3,
                extra_headers={
                    "HTTP-Referer": "https://omni-automator.local",
                    "X-Title": "OmniAutomator"
                }
            )
            
            suggestions_text = response.choices[0].message.content
            suggestions = [line.strip() for line in suggestions_text.split('\n') if line.strip() and not line.startswith('#')]
            
            return {
                'suggestions': suggestions[:5],  # Limit to 5 suggestions
                'confidence': 0.8
            }
            
        except Exception as e:
            return {
                'suggestions': [
                    'Check the command syntax and try again',
                    'Verify all required permissions are granted',
                    'Enable sandbox mode for testing',
                    'Check the logs for more detailed error information'
                ],
                'confidence': 0.3
            }
    
    def optimize_workflow(self, workflow_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize workflow execution order and parallelization"""
        if not self.is_available:
            return {
                'optimized_steps': workflow_steps,
                'improvements': [],
                'parallel_groups': []
            }
        
        try:
            workflow_prompt = f"""
Analyze this workflow and suggest optimizations:

WORKFLOW STEPS:
{json.dumps(workflow_steps, indent=2)}

Please suggest:
1. Better execution order
2. Steps that can run in parallel
3. Any improvements or optimizations

Respond in JSON format:
{{
    "optimized_steps": [...],
    "improvements": ["list of improvements"],
    "parallel_groups": [["step1", "step2"], ["step3"]]
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert at workflow optimization. Analyze workflows and suggest improvements."},
                    {"role": "user", "content": workflow_prompt}
                ],
                max_tokens=1000,
                temperature=0.3,
                extra_headers={
                    "HTTP-Referer": "https://omni-automator.local",
                    "X-Title": "OmniAutomator"
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                'optimized_steps': result.get('optimized_steps', workflow_steps),
                'improvements': result.get('improvements', []),
                'parallel_groups': result.get('parallel_groups', [])
            }
            
        except Exception as e:
            self.logger.error(f"Workflow optimization failed: {e}")
            return {
                'optimized_steps': workflow_steps,
                'improvements': ['Enable AI for workflow optimization'],
                'parallel_groups': []
            }
