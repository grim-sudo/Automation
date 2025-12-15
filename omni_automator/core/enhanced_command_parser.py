#!/usr/bin/env python3
"""
Enhanced Command Parser with Flexible NLP Support
Extends base command parser with flexible natural language understanding
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re

from .flexible_nlp import get_nlp_processor, FlexibleNLPProcessor


@dataclass
class EnhancedParseResult:
    """Enhanced parse result with flexibility metrics"""
    action: str
    category: str
    params: Dict[str, Any]
    confidence: float
    raw_command: str
    nlp_variations: List[str]
    matched_pattern: Optional[str]
    flexibility_score: float


class EnhancedCommandParser:
    """Enhanced parser with flexible NLP understanding"""
    
    def __init__(self, base_parser=None):
        self.base_parser = base_parser
        self.nlp_processor = get_nlp_processor()
        
        # Enhanced pattern variations for flexible matching
        self.flexible_patterns = {
            'create_folder': [
                r'create\s+(?:a\s+)?(folder|directory|dir)\s+([\'"]?)([^\'\"]+?)\2(?:\s+(?:in|at|on|inside)\s+(\S+))?',
                r'make\s+(?:a\s+)?(folder|directory|dir)\s+([\'"]?)([^\'\"]+?)\2(?:\s+(?:in|at|on|inside)\s+(\S+))?',
                r'build\s+(?:a\s+)?(folder|directory|dir)\s+([\'"]?)([^\'\"]+?)\2(?:\s+(?:in|at|on|inside)\s+(\S+))?',
                r'setup\s+(?:a\s+)?(folder|directory|dir)\s+([\'"]?)([^\'\"]+?)\2(?:\s+(?:in|at|on|inside)\s+(\S+))?',
                r'(?:create|make)\s+([a-zA-Z0-9_]+)\s+(?:folder|directory|dir)(?:\s+(?:in|at|on|inside)\s+(\S+))?',
            ],
            'deploy_container': [
                r'deploy\s+([\'"]?)([^\'\"]+)\1\s+(?:using|with|via)\s+(?:docker|container)(?:\s+on\s+(\S+))?',
                r'(?:launch|release|publish)\s+([\'"]?)([^\'\"]+)\1\s+(?:in|via)\s+(?:docker|container)(?:\s+on\s+(\S+))?',
                r'containerize\s+(?:and\s+)?deploy\s+([\'"]?)([^\'\"]+)\1(?:\s+on\s+(\S+))?',
                r'(?:docker|containerize)\s+([\'"]?)([^\'\"]+)\1\s+(?:and\s+)?(?:deploy|launch)(?:\s+on\s+(\S+))?',
            ],
            'setup_database': [
                r'setup\s+(?:a\s+)?(?:database|db)\s+([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using|type)\s+(\S+))?',
                r'create\s+(?:a\s+)?(?:database|db)\s+([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using|type)\s+(\S+))?',
                r'initialize\s+(?:a\s+)?(?:database|db)\s+([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using|type)\s+(\S+))?',
                r'(?:setup|create)\s+([\'"]?)([^\'\"]+?)\1\s+(?:database|db)(?:\s+(?:with|using|type)\s+(\S+))?',
            ],
            'create_pipeline': [
                r'create\s+(?:a\s+)?(?:pipeline|workflow|process)\s+([\'"]?)([^\'\"]+?)\1(?:\s+with\s+(.+?))?(?:\s+(?:for|in|on)\s+(\S+))?',
                r'setup\s+(?:a\s+)?(?:pipeline|workflow|process)\s+([\'"]?)([^\'\"]+?)\1(?:\s+with\s+(.+?))?(?:\s+(?:for|in|on)\s+(\S+))?',
                r'build\s+(?:a\s+)?(?:ci\/cd\s+)?(?:pipeline|workflow|process)\s+([\'"]?)([^\'\"]+?)\1(?:\s+with\s+(.+?))?(?:\s+(?:for|in|on)\s+(\S+))?',
                r'(?:build|create|setup)\s+([\'"]?)([^\'\"]+?)\1\s+(?:pipeline|workflow|process)(?:\s+with\s+(.+?))?(?:\s+(?:for|in|on)\s+(\S+))?',
            ],
            'deploy_kubernetes': [
                r'deploy\s+(?:to\s+)?(?:kubernetes|k8s|k3s)\s+([\'"]?)([^\'\"]+?)\1(?:\s+with\s+(.+?))?',
                r'orchestrate\s+([\'"]?)([^\'\"]+?)\1\s+(?:on\s+)?(?:kubernetes|k8s)(?:\s+with\s+(.+?))?',
                r'(?:setup|create)\s+(?:kubernetes|k8s)\s+(?:deployment|cluster)\s+(?:for\s+)?([\'"]?)([^\'\"]+?)\1(?:\s+with\s+(.+?))?',
                r'(?:kubernetes|k8s)\s+deploy\s+([\'"]?)([^\'\"]+?)\1(?:\s+with\s+(.+?))?',
            ],
            'monitor_service': [
                r'monitor\s+(?:the\s+)?(?:service|app|application)\s+([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using)\s+(.+?))?',
                r'setup\s+(?:monitoring|observability|surveillance)\s+(?:for\s+)?([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using)\s+(.+?))?',
                r'watch\s+(?:the\s+)?(?:service|app)\s+([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using)\s+(.+?))?',
                r'(?:observe|track|supervise)\s+(?:service|app)\s+([\'"]?)([^\'\"]+?)\1(?:\s+(?:with|using)\s+(.+?))?',
            ],
            'backup_data': [
                r'(?:backup|copy|duplicate)\s+(?:data\s+)?(?:from|of)\s+([\'"]?)([^\'\"]+?)\1\s+(?:to|in)\s+([\'"]?)([^\'\"]+?)\4',
                r'(?:create|make)\s+(?:a\s+)?backup\s+of\s+([\'"]?)([^\'\"]+?)\1\s+(?:to|in)\s+([\'"]?)([^\'\"]+?)\4',
                r'(?:backup|replicate)\s+([\'"]?)([^\'\"]+?)\1\s+to\s+([\'"]?)([^\'\"]+?)\4',
                r'save\s+(?:copy\s+of\s+)?([\'"]?)([^\'\"]+?)\1\s+(?:to|as|in)\s+([\'"]?)([^\'\"]+?)\4',
            ],
            'migrate_data': [
                r'migrate\s+([\'"]?)([^\'\"]+?)\1\s+(?:from|to)\s+([\'"]?)([^\'\"]+?)\4(?:\s+using\s+(.+?))?',
                r'(?:move|port|transfer)\s+([\'"]?)([^\'\"]+?)\1\s+(?:from|to)\s+([\'"]?)([^\'\"]+?)\4(?:\s+using\s+(.+?))?',
                r'migrate\s+([\'"]?)([^\'\"]+?)\1\s+to\s+([\'"]?)([^\'\"]+?)\4\s+from\s+(.+?)$',
                r'convert\s+(?:and\s+)?migrate\s+([\'"]?)([^\'\"]+?)\1\s+to\s+([\'"]?)([^\'\"]+?)\4',
            ],
            'create_app': [
                r'create\s+(?:a\s+)?([a-z]+(?:\s+[a-z]+)?)\s+(?:application|app|project)\s+(?:called|named|for|in)\s+([\'"]?)([^\'\"]+?)\2',
                r'(?:generate|scaffold|build)\s+(?:a\s+)?([a-z]+(?:\s+[a-z]+)?)\s+(?:application|app|project)(?:\s+(?:called|named|for)\s+([\'"]?)([^\'\"]+?)\2)?',
                r'(?:setup|initialize)\s+(?:new\s+)?([a-z]+(?:\s+[a-z]+)?)\s+(?:application|app)\s+(?:called|named)\s+([\'"]?)([^\'\"]+?)\2',
                r'create\s+([a-z]+(?:\s+[a-z]+)?)\s+(?:app|application)\s+([\'"]?)([^\'\"]+?)\2',
            ],
        }
    
    def parse_flexible(self, command: str) -> EnhancedParseResult:
        """Parse command with flexible NLP"""
        # Get NLP processing
        nlp_var = self.nlp_processor.process_flexible(command)
        
        # Try to match against flexible patterns
        best_match = None
        best_score = 0
        best_category = None
        best_action = None
        best_match = None
        best_pattern = None
        
        command_lower = command.lower()
        
        # Try all flexible patterns
        for category, patterns in self.flexible_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, command_lower, re.IGNORECASE)
                if match:
                    score = self._calculate_pattern_score(pattern, command_lower)
                    
                    if score > best_score:
                        best_score = score
                        best_match = match
                        best_pattern = pattern
                        best_category = category
                        best_action = category.replace('_', ' ').title()
        
        # Extract parameters
        params = {}
        if best_match:
            params = self._extract_params_from_match(best_match, best_category)
        
        # Also use the base parser if available
        if self.base_parser and not best_match:
            try:
                base_result = self.base_parser.parse(command)
                if base_result:
                    return EnhancedParseResult(
                        action=base_result.get('action', 'unknown'),
                        category=base_result.get('category', 'unknown'),
                        params=base_result.get('params', {}),
                        confidence=base_result.get('confidence', 0.5),
                        raw_command=command,
                        nlp_variations=nlp_var.alternatives,
                        matched_pattern=None,
                        flexibility_score=nlp_var.flexibility_score
                    )
            except:
                pass
        
        # Return enhanced result
        return EnhancedParseResult(
            action=best_action or 'unknown',
            category=best_category or 'unknown',
            params=params,
            confidence=best_score,
            raw_command=command,
            nlp_variations=nlp_var.alternatives,
            matched_pattern=best_pattern,
            flexibility_score=nlp_var.flexibility_score
        )
    
    def _calculate_pattern_score(self, pattern: str, command: str) -> float:
        """Calculate how well pattern matches command"""
        # Count matching words
        pattern_words = set(re.findall(r'\w+', pattern.lower()))
        command_words = set(re.findall(r'\w+', command.lower()))
        
        if not pattern_words:
            return 0.0
        
        intersection = len(pattern_words & command_words)
        return intersection / len(pattern_words)
    
    def _extract_params_from_match(self, match, category: str) -> Dict[str, Any]:
        """Extract parameters from regex match"""
        params = {}
        
        groups = match.groups()
        
        if category == 'create_folder':
            if len(groups) >= 3:
                params['name'] = groups[2]
                if len(groups) > 3 and groups[3]:
                    params['location'] = groups[3]
        
        elif category == 'deploy_container':
            if len(groups) >= 2:
                params['app_name'] = groups[1]
                if len(groups) > 2 and groups[2]:
                    params['target'] = groups[2]
        
        elif category == 'setup_database':
            if len(groups) >= 2:
                params['db_name'] = groups[1]
                if len(groups) > 2 and groups[2]:
                    params['db_type'] = groups[2]
        
        elif category == 'create_pipeline':
            if len(groups) >= 2:
                params['pipeline_name'] = groups[1]
                if len(groups) > 2 and groups[2]:
                    params['features'] = [f.strip() for f in groups[2].split(',')]
        
        elif category == 'deploy_kubernetes':
            if len(groups) >= 2:
                params['app_name'] = groups[1]
                if len(groups) > 2 and groups[2]:
                    params['config'] = groups[2]
        
        elif category == 'backup_data':
            if len(groups) >= 4:
                params['source'] = groups[1]
                params['destination'] = groups[3]
        
        elif category == 'migrate_data':
            if len(groups) >= 4:
                params['source_name'] = groups[1]
                params['source_type'] = groups[2]
                params['target_name'] = groups[3]
                params['target_type'] = groups[4] if len(groups) > 4 else None
        
        elif category == 'create_app':
            if len(groups) >= 3:
                params['app_type'] = groups[0]
                params['app_name'] = groups[2]
        
        return params
    
    def supports_variation(self, command: str) -> bool:
        """Check if command supports flexible NLP"""
        nlp_var = self.nlp_processor.process_flexible(command)
        return nlp_var.flexibility_score > 0.3
    
    def get_command_variations(self, command: str) -> List[str]:
        """Get supported variations of a command"""
        nlp_var = self.nlp_processor.process_flexible(command)
        
        variations = [command]
        variations.extend(nlp_var.alternatives)
        variations.extend(nlp_var.synonyms)
        
        return list(set(variations))  # Remove duplicates


# Export enhanced parser
__all__ = ['EnhancedCommandParser', 'EnhancedParseResult']
