"""
AI-Enhanced command parser using DeepSeek R1 T2 Chimera for intelligent interpretation
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .advanced_parser import AdvancedCommandParser, ComplexCommand, ParsedStep, CommandComplexity
from ..ai.openrouter_integration import OpenRouterAutomationAI, AITaskPlan
from ..utils.logger import get_logger


class AIEnhancedParser:
    """Command parser enhanced with OpenRouter AI for superior natural language understanding"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.logger = get_logger("AIEnhancedParser")
        self.fallback_parser = AdvancedCommandParser()
        self.openrouter_ai = OpenRouterAutomationAI(api_key)
        
        # Learning and adaptation
        self.user_patterns = {}
        self.command_history = []
    
    def parse_with_ai(self, command: str, context: Dict[str, Any] = None) -> ComplexCommand:
        """Parse command using AI enhancement"""
        
        # Add to command history for learning
        self.command_history.append(command)
        if len(self.command_history) > 50:  # Keep last 50 commands
            self.command_history = self.command_history[-50:]
        
        if self.openrouter_ai.is_openrouter_available():
            return self._parse_with_openrouter(command, context)
        else:
            self.logger.info("OpenRouter AI not available, using fallback parser")
            return self.fallback_parser.parse_complex_command(command)
    
    def _parse_with_openrouter(self, command: str, context: Dict[str, Any] = None) -> ComplexCommand:
        """Parse command using OpenRouter AI"""
        
        try:
            # For very long commands, check if AI can handle it
            # If command is very long and complex, use fallback parser directly
            if len(command) > 200 and self._is_complex_structure(command):
                self.logger.info("Complex command detected, using fallback parser for better accuracy")
                return self.fallback_parser.parse_complex_command(command)
            
            # Enhance command understanding with AI
            enhancement = self.openrouter_ai.enhance_command_understanding(
                command, 
                self.command_history[-5:]  # Recent history for context
            )
            
            enhanced_command = enhancement.get('enhanced_command', command)
            self.logger.info(f"AI enhanced command: {enhanced_command}")
            
            # Get AI task plan
            ai_plan = self.openrouter_ai.analyze_automation_request(enhanced_command, context)
            
            # Check if AI plan has valid steps
            if not ai_plan.execution_steps or len(ai_plan.execution_steps) == 0:
                self.logger.warning("AI returned empty steps, using fallback parser")
                return self.fallback_parser.parse_complex_command(command)
            
            # Validate AI steps have required fields
            valid_steps = []
            for step in ai_plan.execution_steps:
                if isinstance(step, dict) and step.get('action') and step.get('category'):
                    valid_steps.append(step)
                else:
                    self.logger.warning(f"Invalid AI step: {step}")
            
            if not valid_steps:
                self.logger.warning("No valid AI steps found, using fallback parser")
                return self.fallback_parser.parse_complex_command(command)
            
            # Update AI plan with valid steps
            ai_plan.execution_steps = valid_steps
            
            # Convert AI plan to ComplexCommand format
            complex_command = self._convert_ai_plan_to_complex_command(ai_plan)
            
            # Optimize workflow if it's complex
            if len(complex_command.steps) > 2:
                try:
                    optimization = self.openrouter_ai.optimize_workflow([
                        {
                            'action': step.action,
                            'category': step.category,
                            'params': step.params,
                            'priority': step.priority
                        }
                        for step in complex_command.steps
                    ])
                    
                    if optimization and optimization.get('optimized_steps'):
                        complex_command = self._apply_optimizations(complex_command, optimization)
                    
                    # Add optimization info to context
                    if optimization:
                        complex_command.context['ai_optimizations'] = optimization.get('improvements', [])
                        complex_command.context['parallel_groups'] = optimization.get('parallel_groups', [])
                except Exception as opt_error:
                    self.logger.warning(f"Workflow optimization skipped due to: {opt_error}")
                    # Continue without optimization - don't fail the entire parse
            
            return complex_command
            
        except Exception as e:
            self.logger.error(f"AI parsing failed, using fallback: {e}")
            return self.fallback_parser.parse_complex_command(command)
    
    def _convert_ai_plan_to_complex_command(self, ai_plan: AITaskPlan) -> ComplexCommand:
        """Convert AI task plan to ComplexCommand format"""
        
        # Determine complexity from AI analysis (use default since context_analysis doesn't exist)
        ai_complexity = 'compound'  # Default complexity
        complexity_map = {
            'simple': CommandComplexity.SIMPLE,
            'compound': CommandComplexity.COMPOUND,
            'workflow': CommandComplexity.WORKFLOW,
            'conditional': CommandComplexity.CONDITIONAL
        }
        complexity = complexity_map.get(ai_complexity, CommandComplexity.COMPOUND)
        
        # Convert AI steps to ParsedStep objects
        steps = []
        for i, ai_step in enumerate(ai_plan.execution_steps):
            step = ParsedStep(
                action=ai_step.get('action', 'unknown'),
                category=ai_step.get('category', 'unknown'),
                params=ai_step.get('params', {}),
                dependencies=ai_step.get('dependencies', []),
                conditions=ai_step.get('conditions'),
                priority=ai_step.get('priority', i + 1)
            )
            steps.append(step)
        
        # Calculate estimated duration
        estimated_duration = sum(
            step.get('estimated_time', 5) for step in ai_plan.execution_steps
        )
        
        return ComplexCommand(
            original_command=ai_plan.original_request,
            complexity=complexity,
            steps=steps,
            context={},  # Empty context since context_analysis doesn't exist
            estimated_duration=estimated_duration
        )
    
    def _apply_optimizations(self, complex_command: ComplexCommand, optimization: Dict[str, Any]) -> ComplexCommand:
        """Apply AI optimizations to the complex command"""
        
        optimized_steps = optimization.get('optimized_steps', [])
        if not optimized_steps:
            return complex_command
        
        # Update steps with optimizations
        new_steps = []
        for i, opt_step in enumerate(optimized_steps):
            step = ParsedStep(
                action=opt_step.get('action', 'unknown'),
                category=opt_step.get('category', 'unknown'),
                params=opt_step.get('params', {}),
                dependencies=opt_step.get('dependencies', []),
                priority=opt_step.get('priority', i + 1)
            )
            new_steps.append(step)
        
        # Update estimated duration if provided
        if 'estimated_duration' in optimization:
            complex_command.estimated_duration = optimization['estimated_duration']
        
        complex_command.steps = new_steps
        
        # Add optimization info to context
        complex_command.context['ai_optimizations'] = optimization.get('improvements', [])
        complex_command.context['parallel_groups'] = optimization.get('parallel_groups', [])
        
        return complex_command
    
    def get_smart_suggestions(self, context: Dict[str, Any] = None) -> List[str]:
        """Get AI-powered smart suggestions"""
        
        if not self.openrouter_ai.is_openrouter_available():
            return [
                "Set OPENROUTER_API_KEY environment variable for AI suggestions",
                "Try 'examples' for command ideas",
                "Use 'help' to see available commands"
            ]
        
        # Build context from command history and current state
        suggestion_context = context or {}
        suggestion_context['recent_commands'] = self.command_history[-10:]
        suggestion_context['user_patterns'] = self.user_patterns
        
        return self.openrouter_ai.generate_smart_suggestions(suggestion_context)
    
    def analyze_command_intent(self, command: str) -> Dict[str, Any]:
        """Analyze command intent using AI"""
        
        if not self.openrouter_ai.is_openrouter_available():
            return {
                'intent': 'Basic parsing only',
                'confidence': 0.1,
                'suggestions': ['Enable OpenRouter AI for better analysis']
            }
        
        try:
            ai_plan = self.openrouter_ai.analyze_automation_request(command)
            
            return {
                'intent': ai_plan.interpreted_intent,
                'confidence': ai_plan.confidence_score,
                'risks': ai_plan.risk_assessment,
                'optimizations': ai_plan.optimization_suggestions,
                'steps_count': len(ai_plan.execution_steps)
            }
            
        except Exception as e:
            self.logger.error(f"Intent analysis failed: {e}")
            return {
                'intent': 'Analysis failed',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def handle_execution_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI suggestions for handling execution errors"""
        
        if not self.openrouter_ai.is_openrouter_available():
            return {
                'suggestions': ['Check logs and try again'],
                'confidence': 0.1
            }
        
        return self.openrouter_ai.suggest_error_resolution(error_info)
    
    def learn_from_execution(self, command: str, result: Dict[str, Any]):
        """Learn from command execution results"""
        
        # Update user patterns based on successful executions
        if result.get('success'):
            # Extract patterns from successful commands
            if 'create' in command.lower():
                self.user_patterns['prefers_creation'] = self.user_patterns.get('prefers_creation', 0) + 1
            
            if 'project' in command.lower():
                self.user_patterns['works_with_projects'] = self.user_patterns.get('works_with_projects', 0) + 1
            
            # Track complexity preferences
            complexity = result.get('complexity', 'simple')
            pattern_key = f'uses_{complexity}_commands'
            self.user_patterns[pattern_key] = self.user_patterns.get(pattern_key, 0) + 1
    
    def _is_complex_structure(self, command: str) -> bool:
        """Detect if command has complex nested structure"""
        import re
        
        # Check for loop/nesting indicators
        nested_patterns = [
            r'in\s+(?:that|those|each|every)',
            r'and\s+in\s+',
            r'inside\s+(?:each|every|that)',
            r'\d+\s+folders?.*\d+\s+folders?',
            r'table \d+ to table \d+',
        ]
        
        for pattern in nested_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        
        # Check for multiple action conjunctions
        actions = command.lower().count(' and ')
        if actions >= 3:
            return True
        
        return False
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI integration status"""
        return self.openrouter_ai.get_ai_status()
    
    def set_api_key(self, api_key: str) -> bool:
        """Set OpenRouter API key and reinitialize"""
        try:
            self.openrouter_ai = OpenRouterAutomationAI(api_key)
            return self.openrouter_ai.is_openrouter_available()
        except Exception as e:
            self.logger.error(f"Failed to set API key: {e}")
            return False
