"""
Natural language command parser that converts user requests into structured automation commands
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    """Structured representation of a parsed command"""
    action: str
    category: str
    params: Dict[str, Any]
    confidence: float
    raw_command: str


class CommandParser:
    """Parses natural language commands into structured automation instructions"""
    
    def __init__(self):
        self.command_patterns = self._load_command_patterns()
        self.action_mappings = self._load_action_mappings()
    
    def parse(self, command: str) -> Dict[str, Any]:
        """Parse a natural language command into structured format"""
        command = command.strip().lower()
        
        # Try to match against known patterns
        for pattern_info in self.command_patterns:
            match = re.search(pattern_info['pattern'], command, re.IGNORECASE)
            if match:
                return self._build_parsed_command(pattern_info, match, command)
        
        # Fallback: try to extract basic components
        return self._fallback_parse(command)
    
    def _load_command_patterns(self) -> List[Dict[str, Any]]:
        """Load command patterns for different automation categories"""
        return [
            # Filesystem operations
            {
                'pattern': r'create\s+(?:a\s+)?(folder|directory)\s+[\'"]?([^\'"]+)[\'"]?\s*(?:(?:in|at|on)\s+[\'"]?([^\'"]+)[\'"]?)?',
                'category': 'filesystem',
                'action': 'create_folder',
                'params': ['type', 'name', 'location']
            },
            {
                'pattern': r'create\s+(?:a\s+)?file\s+[\'"]?([^\'"]+)[\'"]?\s*(?:(?:in|at|on)\s+[\'"]?([^\'"]+)[\'"]?)?',
                'category': 'filesystem',
                'action': 'create_file',
                'params': ['name', 'location']
            },
            {
                'pattern': r'delete\s+(file|folder|directory)\s+[\'"]?([^\'"]+)[\'"]?',
                'category': 'filesystem',
                'action': 'delete',
                'params': ['type', 'path']
            },
            {
                'pattern': r'copy\s+[\'"]?([^\'"]+)[\'"]?\s+to\s+[\'"]?([^\'"]+)[\'"]?',
                'category': 'filesystem',
                'action': 'copy',
                'params': ['source', 'destination']
            },
            {
                'pattern': r'move\s+[\'"]?([^\'"]+)[\'"]?\s+to\s+[\'"]?([^\'"]+)[\'"]?',
                'category': 'filesystem',
                'action': 'move',
                'params': ['source', 'destination']
            },
            
            # Process operations
            {
                'pattern': r'(?:open|start|launch|run)\s+([^\s]+)(?:\s+with\s+args?\s+[\'"]?([^\'"]*)[\'"]?)?',
                'category': 'process',
                'action': 'start',
                'params': ['program', 'args']
            },
            {
                'pattern': r'(?:close|kill|terminate|stop)\s+([^\s]+)',
                'category': 'process',
                'action': 'terminate',
                'params': ['program']
            },
            {
                'pattern': r'list\s+(?:running\s+)?processes',
                'category': 'process',
                'action': 'list',
                'params': []
            },
            
            # GUI operations
            {
                'pattern': r'click\s+(?:on\s+)?(?:button\s+)?[\'"]?([^\'"]+)[\'"]?(?:\s+at\s+(\d+),\s*(\d+))?',
                'category': 'gui',
                'action': 'click',
                'params': ['target', 'x', 'y']
            },
            {
                'pattern': r'type\s+[\'"]([^\'"]+)[\'"]',
                'category': 'gui',
                'action': 'type',
                'params': ['text']
            },
            {
                'pattern': r'press\s+(?:key\s+)?([^\s]+)',
                'category': 'gui',
                'action': 'press_key',
                'params': ['key']
            },
            {
                'pattern': r'take\s+screenshot(?:\s+(?:and\s+)?save\s+as\s+[\'"]?([^\'"]+)[\'"]?)?',
                'category': 'gui',
                'action': 'screenshot',
                'params': ['filename']
            },
            {
                'pattern': r'wait\s+(\d+)\s*(?:seconds?|secs?|s)?',
                'category': 'gui',
                'action': 'wait',
                'params': ['duration']
            },
            
            # System operations
            {
                'pattern': r'(?:get|show|display)\s+system\s+info(?:rmation)?',
                'category': 'system',
                'action': 'get_info',
                'params': []
            },
            {
                'pattern': r'set\s+volume\s+to\s+(\d+)(?:%)?',
                'category': 'system',
                'action': 'set_volume',
                'params': ['level']
            },
            {
                'pattern': r'(?:shutdown|restart|reboot)\s*(?:computer|system|pc)?',
                'category': 'system',
                'action': 'power_action',
                'params': ['action']
            },
            
            # Network operations
            {
                'pattern': r'download\s+[\'"]?([^\'"]+)[\'"]?(?:\s+(?:to|as)\s+[\'"]?([^\'"]+)[\'"]?)?',
                'category': 'network',
                'action': 'download',
                'params': ['url', 'filename']
            },
            {
                'pattern': r'(?:get|fetch)\s+[\'"]?([^\'"]+)[\'"]?',
                'category': 'network',
                'action': 'http_get',
                'params': ['url']
            },
            
            # File monitoring
            {
                'pattern': r'watch\s+(?:folder\s+)?[\'"]?([^\'"]+)[\'"]?(?:\s+for\s+changes)?',
                'category': 'monitoring',
                'action': 'watch_folder',
                'params': ['path']
            },
            
            # Project generation patterns
            {
                'pattern': r'create\s+(?:a\s+)?(?:folder|directory)\s+[\'"]?([^\'"]+)[\'"]?\s+and.*?c\s+program.*?addition',
                'category': 'project_generator',
                'action': 'create_c_project',
                'params': ['name']
            },
            {
                'pattern': r'create\s+(?:a\s+)?c\s+(?:program|project)\s+[\'"]?([^\'"]+)[\'"]?.*?addition',
                'category': 'project_generator', 
                'action': 'create_c_program',
                'params': ['name']
            }
        ]
    
    def _load_action_mappings(self) -> Dict[str, str]:
        """Load mappings from common words to action names"""
        return {
            'make': 'create',
            'build': 'create',
            'new': 'create',
            'remove': 'delete',
            'erase': 'delete',
            'destroy': 'delete',
            'execute': 'run',
            'launch': 'start',
            'begin': 'start',
            'end': 'stop',
            'quit': 'stop',
            'exit': 'stop'
        }
    
    def _build_parsed_command(self, pattern_info: Dict[str, Any], match: re.Match, 
                            original_command: str) -> Dict[str, Any]:
        """Build a parsed command from pattern match"""
        params = {}
        
        # Extract parameters from regex groups
        groups = match.groups()
        param_names = pattern_info.get('params', [])
        
        for i, param_name in enumerate(param_names):
            if i < len(groups) and groups[i] is not None:
                params[param_name] = groups[i].strip()
        
        # Handle special cases
        if pattern_info['category'] == 'filesystem' and 'location' not in params:
            params['location'] = self._get_default_location(pattern_info['action'])
        
        return {
            'action': pattern_info['action'],
            'category': pattern_info['category'],
            'params': params,
            'confidence': 0.9,
            'raw_command': original_command
        }
    
    def _fallback_parse(self, command: str) -> Dict[str, Any]:
        """Fallback parser for unrecognized commands"""
        words = command.split()
        
        if not words:
            return {
                'action': 'unknown',
                'category': 'unknown',
                'params': {},
                'confidence': 0.1,
                'raw_command': command
            }
        
        # Try to identify action verb
        action_word = words[0]
        if action_word in self.action_mappings:
            action_word = self.action_mappings[action_word]
        
        # Try to identify category based on keywords
        category = self._identify_category(command)
        
        return {
            'action': action_word,
            'category': category,
            'params': {'raw_args': ' '.join(words[1:]) if len(words) > 1 else ''},
            'confidence': 0.3,
            'raw_command': command
        }
    
    def _identify_category(self, command: str) -> str:
        """Identify command category from keywords"""
        filesystem_keywords = ['file', 'folder', 'directory', 'path', 'copy', 'move', 'delete']
        process_keywords = ['process', 'program', 'application', 'run', 'start', 'kill']
        gui_keywords = ['click', 'type', 'key', 'mouse', 'screen', 'window']
        system_keywords = ['system', 'volume', 'shutdown', 'restart', 'registry']
        network_keywords = ['download', 'url', 'http', 'web', 'internet']
        
        command_lower = command.lower()
        
        if any(keyword in command_lower for keyword in filesystem_keywords):
            return 'filesystem'
        elif any(keyword in command_lower for keyword in process_keywords):
            return 'process'
        elif any(keyword in command_lower for keyword in gui_keywords):
            return 'gui'
        elif any(keyword in command_lower for keyword in system_keywords):
            return 'system'
        elif any(keyword in command_lower for keyword in network_keywords):
            return 'network'
        else:
            return 'unknown'
    
    def _get_default_location(self, action: str) -> str:
        """Get default location for filesystem operations"""
        import os
        
        if action in ['create_folder', 'create_file']:
            # Default to desktop for creation operations
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            if os.path.exists(desktop):
                return desktop
            else:
                return os.path.expanduser('~')
        
        return os.getcwd()
    
    def get_suggestions(self, partial_command: str) -> List[str]:
        """Get command suggestions based on partial input"""
        suggestions = []
        partial_lower = partial_command.lower()
        
        # Common command templates
        templates = [
            "create folder 'folder_name'",
            "create file 'filename.txt'",
            "open notepad",
            "take screenshot",
            "click on 'button_name'",
            "type 'your text here'",
            "download 'url'",
            "copy 'source' to 'destination'",
            "delete file 'filename'",
            "list processes"
        ]
        
        for template in templates:
            if template.startswith(partial_lower):
                suggestions.append(template)
        
        return suggestions[:5]  # Return top 5 suggestions
