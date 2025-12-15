"""
Natural language command parser that converts user requests into structured automation commands
"""

import re
import json
import os
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
        
        # Preprocess: remove common filler words and phrases
        command = self._preprocess_command(command)
        
        # Try to match against known patterns
        for pattern_info in self.command_patterns:
            match = re.search(pattern_info['pattern'], command, re.IGNORECASE)
            if match:
                return self._build_parsed_command(pattern_info, match, command)
        
        # Fallback: try to extract basic components
        return self._fallback_parse(command)
    
    def _preprocess_command(self, command: str) -> str:
        """Remove filler words and phrases to normalize input"""
        # Common filler words and phrases to remove from start
        filler_patterns = [
            r'^(please|kindly|can you|could you|would you|will you)\s+',
            r'^(i\s+(?:need|want|wish|would\s+like))\s+',
            r'^(hey|hello|hi|ok|okay|alright)\s+',
            r'^(to)\s+',  # Remove leading "to" that results from other removals
        ]
        
        for pattern in filler_patterns:
            command = re.sub(pattern, '', command, flags=re.IGNORECASE)
        
        # Normalize common phrase variations
        # "make a folder called X" -> "create folder X"
        command = re.sub(r'\bcalled\s+', '', command)
        command = re.sub(r'\bnamed\s+', '', command)
        command = re.sub(r'\ba\s+folder\b', 'folder', command)
        command = re.sub(r'\ba\s+file\b', 'file', command)
        command = re.sub(r'\ba\s+directory\b', 'directory', command)
        
        return command.strip()
    
    def _load_command_patterns(self) -> List[Dict[str, Any]]:
        """Load command patterns for different automation categories"""
        return [
            # Filesystem operations - With explicit handling of location
            {
                'pattern': r'create\s+(?:a\s+)?(folder|directory)\s+([\'"])([^\'"]+?)\2\s*(?:(?:in|at|on)\s+([\'"]?)([^\'"]+?)\4)?',
                'category': 'filesystem',
                'action': 'create_folder',
                'params': ['type', 'name_quote', 'name', 'location_quote', 'location']
            },
            # Version for unquoted names with location
            {
                'pattern': r'create\s+(?:a\s+)?(folder|directory)\s+(\S+)\s+(?:in|at|on)\s+(\S+)$',
                'category': 'filesystem',
                'action': 'create_folder',
                'params': ['type', 'name', 'location']
            },
            # Version for unquoted names without location
            {
                'pattern': r'create\s+(?:a\s+)?(folder|directory)\s+(\S+)$',
                'category': 'filesystem',
                'action': 'create_folder',
                'params': ['type', 'name']
            },
            # Version for name-first format: "create test3 folder"
            {
                'pattern': r'create\s+([a-zA-Z0-9_]+)\s+(folder|directory)\s*(?:(?:on|in|at)\s+(\S+))?$',
                'category': 'filesystem',
                'action': 'create_folder',
                'params': ['name', 'type', 'location']
            },
            # Batch folder creation: "create 10 folders from project1 to project10"
            {
                'pattern': r'create\s+(\d+)\s+(?:folders?|directories?)\s+(?:(?:from|named)\s+)?(\S+?)\s+to\s+(\S+)\s*(?:(?:on|in|at)\s+(\S+))?$',
                'category': 'filesystem',
                'action': 'create_folders_batch',
                'params': ['count', 'start_name', 'end_name', 'location']
            },
            # Batch folder creation with "on desktop" style
            {
                'pattern': r'create\s+(\d+)\s+(?:folders?|directories?)\s+(?:on|in|at)\s+(\S+)\s+(?:(?:from|named)\s+)?(\S+?)\s+to\s+(\S+)',
                'category': 'filesystem',
                'action': 'create_folders_batch',
                'params': ['count', 'location', 'start_name', 'end_name']
            },
            # Create file patterns - properly handle quoted and unquoted names with locations
            {
                'pattern': r'create\s+(?:a\s+)?file\s+([\'"])([^\'"]+?)\1\s*(?:(?:in|at|on)\s+([\'"])([^\'"]+?)\3)?',
                'category': 'filesystem',
                'action': 'create_file',
                'params': ['name_quote1', 'name', 'location_quote1', 'location']
            },
            {
                'pattern': r'create\s+(?:a\s+)?file\s+(\S+)\s+(?:in|at|on)\s+(\S+)$',
                'category': 'filesystem',
                'action': 'create_file',
                'params': ['name', 'location']
            },
            {
                'pattern': r'create\s+(?:a\s+)?file\s+(\S+)$',
                'category': 'filesystem',
                'action': 'create_file',
                'params': ['name']
            },
            # Delete patterns
            {
                'pattern': r'delete\s+(file|folder|directory)\s+([\'"])([^\'"]+?)\2',
                'category': 'filesystem',
                'action': 'delete',
                'params': ['type', 'path_quote', 'path']
            },
            {
                'pattern': r'delete\s+(file|folder|directory)\s+(\S+)$',
                'category': 'filesystem',
                'action': 'delete',
                'params': ['type', 'path']
            },
            # Copy patterns - properly handle quoted and unquoted paths
            {
                'pattern': r'copy\s+([\'"])([^\'"]+?)\1\s+to\s+([\'"])([^\'"]+?)\3',
                'category': 'filesystem',
                'action': 'copy',
                'params': ['source_quote', 'source', 'dest_quote', 'destination']
            },
            {
                'pattern': r'copy\s+(\S+)\s+to\s+(\S+)$',
                'category': 'filesystem',
                'action': 'copy',
                'params': ['source', 'destination']
            },
            # Move patterns - properly handle quoted and unquoted paths
            {
                'pattern': r'move\s+([\'"])([^\'"]+?)\1\s+to\s+([\'"])([^\'"]+?)\3',
                'category': 'filesystem',
                'action': 'move',
                'params': ['source_quote', 'source', 'dest_quote', 'destination']
            },
            {
                'pattern': r'move\s+(\S+)\s+to\s+(\S+)$',
                'category': 'filesystem',
                'action': 'move',
                'params': ['source', 'destination']
            },
            
            # ENTERPRISE DEVOPS PATTERNS
            # CI/CD Pipeline patterns
            {
                'pattern': r'(?:create|setup|generate)\s+(?:a\s+)?(?:cicd?|ci[\s/\\-]?cd)\s+(?:pipeline|workflow)(?:\s+(?:for|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'setup_ci_cd_pipeline',
                'params': ['tech_stack']
            },
            # Docker patterns
            {
                'pattern': r'(?:create|generate)\s+(?:a\s+)?dockerfile(?:\s+(?:for|with)\s+([a-zA-Z0-9]+))?(?:\s+(?:at|in|on)\s+([^\s]+))?',
                'category': 'devops',
                'action': 'create_dockerfile',
                'params': ['app_type', 'location']
            },
            # Kubernetes patterns
            {
                'pattern': r'(?:create|generate|setup)\s+(?:a\s+)?kubernetes\s+(?:cluster|manifests?)(?:\s+(?:for|with)\s+([a-zA-Z0-9]+))?',
                'category': 'devops',
                'action': 'create_kubernetes_manifest',
                'params': ['app_type']
            },
            # Docker Compose patterns
            {
                'pattern': r'(?:create|generate)\s+(?:docker[\s-]?compose|compose\s+file)(?:\s+(?:for|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_docker_compose',
                'params': ['services']
            },
            # ML/AI patterns
            {
                'pattern': r'(?:create|setup|generate)\s+(?:a\s+)?(?:machine\s+learning|ml|ai)\s+(?:pipeline|framework|project)(?:\s+(?:for|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_ml_pipeline',
                'params': ['tech_stack']
            },
            # Web application patterns
            {
                'pattern': r'(?:create|generate)\s+(?:a\s+)?(?:web\s+)?(?:react|vue|angular|django|flask|nextjs?)\s+(?:application|app|project)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'project_generator',
                'action': 'create_web_project',
                'params': ['framework', 'features']
            },
            # Project generation patterns
            {
                'pattern': r'(?:create|generate)\s+(?:a\s+)?(?:python|java|node|go|rust|csharp|cpp|javascript|typescript)\s+(?:project|application|app)(?:\s+named?\s+([a-zA-Z0-9\-_]+))?(?:\s+(?:at|in|on)\s+([^\s]+))?',
                'category': 'project_generator',
                'action': 'create_programming_project',
                'params': ['language', 'name', 'location']
            },
            # GitHub Actions patterns
            {
                'pattern': r'(?:create|setup|generate)\s+(?:github\s+actions|gh\s+actions)\s+(?:workflow|pipeline)(?:\s+(?:for|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_github_actions',
                'params': ['workflow_type']
            },
            # Jenkins patterns
            {
                'pattern': r'(?:create|setup|generate)\s+(?:jenkins|jenkins\s+pipeline)\s+(?:pipeline|workflow)(?:\s+(?:for|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_jenkins_pipeline',
                'params': ['pipeline_type']
            },
            # Monitoring patterns
            {
                'pattern': r'(?:setup|create|configure)\s+(?:monitoring|observability)\s+(?:with|using|for)\s+([a-zA-Z0-9\s,\-]+)',
                'category': 'devops',
                'action': 'setup_monitoring',
                'params': ['tools']
            },
            # Infrastructure as Code patterns
            {
                'pattern': r'(?:create|generate)\s+(?:terraform|aws|azure|gcp)\s+(?:config|configuration|infrastructure)(?:\s+(?:for|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_terraform_config',
                'params': ['cloud_provider']
            },
            
            # ADVANCED README EXAMPLES PATTERNS
            # Database patterns
            {
                'pattern': r'(?:setup|create|generate)\s+(?:postgresql|mysql|mongodb|redis|database)\s+(?:database|db|system)?(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'setup_database',
                'params': ['db_type', 'features']
            },
            # ETL and Data Pipeline patterns
            {
                'pattern': r'(?:create|setup|generate)\s+(?:data\s+warehouse|etl\s+pipeline|data\s+pipeline)(?:\s+(?:with|for)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_data_pipeline',
                'params': ['tech_stack']
            },
            # Microservices patterns
            {
                'pattern': r'(?:deploy|create|setup)\s+(?:microservices?\s+)?(?:architecture|system)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_microservices',
                'params': ['features']
            },
            # Cloud deployment patterns (AWS, Azure, GCP)
            {
                'pattern': r'(?:deploy|setup)\s+(?:to\s+)?(?:aws|azure|gcp|google\s+cloud|amazon)\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+)',
                'category': 'devops',
                'action': 'cloud_deployment',
                'params': ['features']
            },
            # Serverless patterns
            {
                'pattern': r'(?:create|setup)\s+(?:serverless\s+)?(?:architecture|system)(?:\s+with\s+(?:lambda|functions|azure\s+functions))?',
                'category': 'devops',
                'action': 'create_serverless',
                'params': []
            },
            # Mobile app patterns
            {
                'pattern': r'(?:create|generate)\s+(?:mobile\s+)?(?:app|application)\s+(?:with|using)\s+([a-zA-Z0-9\s,\-]+)',
                'category': 'project_generator',
                'action': 'create_mobile_app',
                'params': ['framework']
            },
            # MLOps patterns
            {
                'pattern': r'(?:setup|create)\s+(?:mlops|ml\s+ops)\s+(?:platform|system)(?:\s+with|including)\s+([a-zA-Z0-9\s,\-]+)?',
                'category': 'devops',
                'action': 'setup_mlops',
                'params': ['tools']
            },
            # Security audit patterns
            {
                'pattern': r'(?:perform|conduct|run)\s+(?:security\s+)?(?:audit|scan)(?:\s+(?:and|with)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'security_audit',
                'params': ['options']
            },
            # Compliance automation patterns
            {
                'pattern': r'(?:implement|setup|create)\s+(?:gdpr|hipaa|soc2|compliance)\s+(?:automation|system)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'compliance_automation',
                'params': ['standard']
            },
            # Zero-trust security patterns
            {
                'pattern': r'(?:setup|create|implement)\s+(?:zero[\s-]?trust|zero\s+trust)\s+(?:network|architecture)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'zero_trust_setup',
                'params': ['features']
            },
            # E-commerce platform patterns
            {
                'pattern': r'(?:create|build)\s+(?:e[\s-]?commerce|e[\s-]?business)\s+(?:platform|system)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_ecommerce',
                'params': ['features']
            },
            # IoT patterns
            {
                'pattern': r'(?:build|create|setup)\s+(?:iot|smart\s+home)\s+(?:system|platform|application)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_iot_system',
                'params': ['features']
            },
            # Blockchain patterns
            {
                'pattern': r'(?:setup|create|build)\s+(?:blockchain|smart\s+contract|defi|web3)\s+(?:network|system|platform)?(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_blockchain',
                'params': ['features']
            },
            # Disaster recovery patterns
            {
                'pattern': r'(?:setup|create|implement)\s+(?:disaster\s+recovery|dr\s+system|failover)(?:\s+(?:with|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'setup_disaster_recovery',
                'params': ['features']
            },
            # Analytics patterns
            {
                'pattern': r'(?:create|setup|build)\s+(?:analytics\s+)?(?:platform|dashboard|system)(?:\s+(?:with|for|including)\s+([a-zA-Z0-9\s,\-]+))?',
                'category': 'devops',
                'action': 'create_analytics_platform',
                'params': ['tools']
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
                value = groups[i].strip() if isinstance(groups[i], str) else groups[i]
                # Skip quote parameters (they're just markers)
                if not param_name.endswith('_quote'):
                    params[param_name] = value
        
        # Handle special cases
        if pattern_info['category'] == 'filesystem' and 'location' not in params:
            params['location'] = self._get_default_location(pattern_info['action'])
        
        # Expand location if it's a special location like "desktop"
        if 'location' in params and params['location']:
            expanded_location = self._expand_location(params['location'])
            if expanded_location:
                params['location'] = expanded_location
        
        return {
            'action': pattern_info['action'],
            'category': pattern_info['category'],
            'params': params,
            'confidence': 0.9,
            'raw_command': original_command
        }
    
    def _fallback_parse(self, command: str) -> Dict[str, Any]:
        """Enhanced fallback parser with intelligent NLP"""
        words = command.split()
        
        if not words:
            return {
                'action': 'unknown',
                'category': 'unknown',
                'params': {},
                'confidence': 0.1,
                'raw_command': command
            }
        
        # Intelligent action extraction
        action_word = words[0].lower()
        
        # Map common variations to actions
        action_mappings = {
            'create': 'create', 'make': 'make', 'build': 'build', 'new': 'create',
            'delete': 'delete', 'remove': 'delete', 'erase': 'delete', 'destroy': 'delete',
            'copy': 'copy', 'duplicate': 'copy', 'clone': 'copy',
            'move': 'move', 'rename': 'move', 'transfer': 'move',
            'open': 'open', 'start': 'start', 'launch': 'start', 'run': 'run',
            'close': 'close', 'stop': 'stop', 'quit': 'close', 'exit': 'exit',
            'take': 'take', 'get': 'get', 'download': 'download', 'upload': 'upload',
            'setup': 'setup', 'configure': 'setup', 'install': 'install',
            'deploy': 'deploy', 'release': 'deploy', 'publish': 'publish',
            'generate': 'generate', 'scaffold': 'generate',
            'process': 'process', 'convert': 'convert', 'transform': 'transform',
            # Enterprise/DevOps actions
            'dockerize': 'create_dockerfile', 'containerize': 'create_dockerfile',
            'orchestrate': 'create_kubernetes_manifest', 'kubernetes': 'create_kubernetes_manifest',
            'pipeline': 'setup_ci_cd_pipeline', 'workflow': 'setup_ci_cd_pipeline',
            'monitor': 'setup_monitoring', 'observe': 'setup_monitoring',
            'provision': 'setup', 'migrate': 'move',
            'model': 'create_ml_pipeline', 'train': 'create_ml_pipeline',
        }
        
        action = action_mappings.get(action_word, action_word)
        
        # Intelligent category detection
        category = self._identify_category_advanced(command)
        
        # Extract parameters intelligently
        params = self._extract_params_intelligent(command, action, category)
        
        # Higher confidence for recognized patterns
        confidence = 0.5 if category != 'unknown' else 0.2
        
        return {
            'action': action,
            'category': category,
            'params': params,
            'confidence': confidence,
            'raw_command': command
        }
    
    def _identify_category_advanced(self, command: str) -> str:
        """Advanced category identification using semantic analysis"""
        command_lower = command.lower()
        
        # File/folder operations
        filesystem_keywords = {
            'file': 'filesystem', 'folder': 'filesystem', 'directory': 'filesystem',
            'path': 'filesystem', 'copy': 'filesystem', 'move': 'filesystem',
            'delete': 'filesystem', 'create': 'filesystem', 'mkdir': 'filesystem',
            'touch': 'filesystem', 'remove': 'filesystem', 'rename': 'filesystem'
        }
        
        # Process/application operations
        process_keywords = {
            'process': 'process', 'program': 'process', 'application': 'process',
            'app': 'process', 'run': 'process', 'start': 'process', 'execute': 'process',
            'launch': 'process', 'kill': 'process', 'terminate': 'process', 'stop': 'process',
            'background': 'process', 'foreground': 'process'
        }
        
        # GUI operations
        gui_keywords = {
            'click': 'gui', 'type': 'gui', 'key': 'gui', 'mouse': 'gui',
            'screen': 'gui', 'window': 'gui', 'button': 'gui', 'text': 'gui',
            'screenshot': 'gui', 'capture': 'gui', 'drag': 'gui', 'drop': 'gui'
        }
        
        # System operations
        system_keywords = {
            'system': 'system', 'volume': 'system', 'shutdown': 'system',
            'restart': 'system', 'reboot': 'system', 'sleep': 'system',
            'info': 'system', 'status': 'system', 'registry': 'system',
            'service': 'system', 'permission': 'system', 'environment': 'system'
        }
        
        # Network operations
        network_keywords = {
            'download': 'network', 'upload': 'network', 'url': 'network',
            'http': 'network', 'web': 'network', 'internet': 'network',
            'api': 'network', 'server': 'network', 'client': 'network',
            'ping': 'network', 'request': 'network', 'fetch': 'network'
        }
        
        # Project/development operations
        project_keywords = {
            'project': 'project_generator', 'generate': 'project_generator',
            'scaffold': 'project_generator', 'template': 'project_generator',
            'boilerplate': 'project_generator', 'setup': 'project_generator'
        }
        
        # DevOps operations
        devops_keywords = {
            'docker': 'devops', 'dockerfile': 'devops', 'containerize': 'devops',
            'kubernetes': 'devops', 'k8s': 'devops', 'helm': 'devops',
            'deploy': 'devops', 'deployment': 'devops', 'deploying': 'devops',
            'pipeline': 'devops', 'ci': 'devops', 'cd': 'devops', 'cicd': 'devops',
            'container': 'devops', 'image': 'devops', 'registry': 'devops',
            'terraform': 'devops', 'infrastructure': 'devops', 'iac': 'devops',
            'jenkins': 'devops', 'github': 'devops', 'gitlab': 'devops',
            'aws': 'devops', 'azure': 'devops', 'gcp': 'devops', 'cloud': 'devops',
            'monitoring': 'devops', 'logging': 'devops', 'observability': 'devops',
            'prometheus': 'devops', 'grafana': 'devops', 'elk': 'devops',
            'service': 'devops', 'mesh': 'devops', 'istio': 'devops'
        }
        
        # ML/AI operations
        ml_keywords = {
            'machine': 'devops', 'learning': 'devops', 'ml': 'devops',
            'ai': 'devops', 'model': 'devops', 'training': 'devops',
            'neural': 'devops', 'network': 'devops', 'deep': 'devops',
            'preprocessing': 'devops', 'pipeline': 'devops', 'dataset': 'devops'
        }
        
        # Check which category matches best
        all_keywords = {
            **filesystem_keywords, **process_keywords, **gui_keywords,
            **system_keywords, **network_keywords, **project_keywords, 
            **devops_keywords, **ml_keywords
        }
        
        # Find all matching keywords and their categories
        matches = {}
        for keyword, cat in all_keywords.items():
            if keyword in command_lower:
                matches[cat] = matches.get(cat, 0) + 1
        
        # Return category with most matches, or unknown
        if matches:
            return max(matches, key=matches.get)
        return 'unknown'
    
    def _extract_params_intelligent(self, command: str, action: str, category: str) -> Dict[str, Any]:
        """Intelligently extract parameters from command"""
        params = {}
        command_lower = command.lower()
        
        # Extract location/path if present
        location_keywords = ['on', 'in', 'at', 'into', 'inside', 'within']
        for loc_kw in location_keywords:
            if f' {loc_kw} ' in f' {command_lower} ':
                idx = command_lower.find(f' {loc_kw} ')
                if idx != -1:
                    after_loc = command[idx + len(loc_kw) + 2:].strip()
                    # Get first word/phrase after location keyword
                    potential_loc = after_loc.split()[0] if after_loc else None
                    if potential_loc:
                        expanded = self._expand_location(potential_loc)
                        params['location'] = expanded if expanded else potential_loc
                        break
        
        # Extract numeric counts for batch operations
        import re as regex
        count_match = regex.search(r'(\d+)\s+(?:folders?|files?|times?|copies?)', command_lower)
        if count_match:
            params['count'] = int(count_match.group(1))
        
        # Extract ranges (from X to Y)
        range_match = regex.search(r'from\s+(\S+)\s+to\s+(\S+)', command_lower)
        if range_match:
            params['start_name'] = range_match.group(1)
            params['end_name'] = range_match.group(2)
        
        # Extract filename/folder name
        name_patterns = [
            r'(?:folder|file|directory|named|called)\s+["\']?([^"\']+)["\']?',
            r'(?:to|called|named)\s+["\']?([^"\']+)["\']?'
        ]
        for pattern in name_patterns:
            name_match = regex.search(pattern, command_lower)
            if name_match:
                params['name'] = name_match.group(1).split()[0]  # Get first word
                break
        
        # Extract source and destination for copy/move
        if action in ['copy', 'move']:
            parts = command.split(' to ')
            if len(parts) == 2:
                # Extract what comes after the action and before 'to'
                before_to = parts[0]
                after_action = before_to.split(None, 1)  # Split on first whitespace
                if len(after_action) > 1:
                    params['source'] = after_action[1].strip()
                    params['destination'] = parts[1].strip()
        
        # Extract path for delete operations
        if action == 'delete':
            # Get everything after the delete word
            cmd_words = command.split()
            after_delete = ' '.join(cmd_words[1:]) if len(cmd_words) > 1 else ''
            if after_delete:
                params['path'] = after_delete.strip()
        
        # Add default location if not provided
        if category == 'filesystem' and 'location' not in params:
            params['location'] = self._get_default_location(action)
        
        # Add raw command for reference
        params['raw_command'] = command
        
        return params
    
    def _identify_category(self, command: str) -> str:
        """Identify command category from keywords (kept for backward compatibility)"""
        return self._identify_category_advanced(command)
    
    def _get_default_location(self, action: str) -> str:
        """Get default location for filesystem operations"""
        if action in ['create_folder', 'create_file']:
            # Default to desktop for creation operations
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            if os.path.exists(desktop):
                return desktop
            else:
                return os.path.expanduser('~')
        
        return os.getcwd()
    
    def _expand_location(self, location: Optional[str]) -> Optional[str]:
        """Expand special location names to actual file paths"""
        if not location:
            return None
        
        location_lower = location.lower().strip()
        home = os.path.expanduser('~')
        
        # Special location mappings
        location_mappings = {
            'desktop': os.path.join(home, 'Desktop'),
            'documents': os.path.join(home, 'Documents'),
            'downloads': os.path.join(home, 'Downloads'),
            'pictures': os.path.join(home, 'Pictures'),
            'music': os.path.join(home, 'Music'),
            'videos': os.path.join(home, 'Videos'),
            'home': home,
            '~': home,
            'current': os.getcwd(),
            '.': os.getcwd(),
        }
        
        # Check for special locations first
        if location_lower in location_mappings:
            return location_mappings[location_lower]
        
        # Handle absolute and relative paths
        if os.path.isabs(location):
            return location
        
        # If it's a relative path, resolve it relative to current directory
        resolved_path = os.path.abspath(location)
        return resolved_path
    
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
