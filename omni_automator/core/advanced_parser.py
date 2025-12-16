"""
Advanced command parser for complex, multi-step natural language commands
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CommandComplexity(Enum):
    SIMPLE = "simple"           # Single action
    COMPOUND = "compound"       # Multiple related actions
    WORKFLOW = "workflow"       # Complex multi-step process
    CONDITIONAL = "conditional" # If-then logic


@dataclass
class ParsedStep:
    """A single step in a complex command"""
    action: str
    category: str
    params: Dict[str, Any]
    dependencies: List[int] = None  # Indices of steps this depends on
    conditions: List[str] = None    # Conditions for execution
    priority: int = 0               # Execution priority


@dataclass
class ComplexCommand:
    """A complex command broken down into executable steps"""
    original_command: str
    complexity: CommandComplexity
    steps: List[ParsedStep]
    context: Dict[str, Any]
    estimated_duration: int = 0  # Seconds


class AdvancedCommandParser:
    """Advanced parser for complex natural language commands"""
    
    def __init__(self):
        self.workflow_patterns = self._load_workflow_patterns()
        self.action_keywords = self._load_action_keywords()
        self.context_keywords = self._load_context_keywords()
        self.conjunction_words = ['and', 'then', 'after', 'next', 'also', 'plus', 'followed by']
        self.conditional_words = ['if', 'when', 'unless', 'after', 'before', 'while']
    
    def parse_complex_command(self, command: str) -> ComplexCommand:
        """Parse a complex natural language command into executable steps"""
        
        # Clean and normalize the command
        normalized_command = self._normalize_command(command)
        
        # Determine complexity
        complexity = self._determine_complexity(normalized_command)
        
        # Extract context and intent
        context = self._extract_context(normalized_command)
        
        # Break down into steps based on complexity
        if complexity == CommandComplexity.SIMPLE:
            steps = self._parse_simple_command(normalized_command)
        elif complexity == CommandComplexity.COMPOUND:
            steps = self._parse_compound_command(normalized_command)
        elif complexity == CommandComplexity.WORKFLOW:
            steps = self._parse_workflow_command(normalized_command, context)
        else:  # CONDITIONAL
            steps = self._parse_conditional_command(normalized_command)
        
        # Estimate duration
        duration = self._estimate_duration(steps)
        
        return ComplexCommand(
            original_command=command,
            complexity=complexity,
            steps=steps,
            context=context,
            estimated_duration=duration
        )
    
    def _normalize_command(self, command: str) -> str:
        """Normalize command text for better parsing"""
        # Convert to lowercase
        normalized = command.lower().strip()
        
        # Replace common variations
        replacements = {
            ' & ': ' and ',
            ' + ': ' and ',
            'vs code': 'vscode',
            'visual studio code': 'vscode',
            'notepad++': 'notepadplusplus',
            'web browser': 'browser',
            'internet browser': 'browser',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _determine_complexity(self, command: str) -> CommandComplexity:
        """Determine the complexity level of the command"""
        
        # Check for specific workflow patterns first
        workflow_indicators = [
            'data analysis', 'web scraping', 'development environment', 
            'machine learning', 'full stack', 'complete setup'
        ]
        
        if any(indicator in command for indicator in workflow_indicators):
            return CommandComplexity.WORKFLOW
        
        # Check for data science stack
        data_science_tools = ['pandas', 'matplotlib', 'seaborn', 'jupyter', 'numpy']
        data_science_count = sum(1 for tool in data_science_tools if tool in command)
        if data_science_count >= 3:
            return CommandComplexity.WORKFLOW
        
        # Single-action commands should be SIMPLE, even if they have prepositions like "to", "in", "on"
        simple_actions = ['copy', 'move', 'delete', 'create folder', 'create file', 'rename']
        if any(action in command for action in simple_actions):
            # These are always SIMPLE - one action with parameters
            return CommandComplexity.SIMPLE
        
        # Count conjunctions and conditional words
        conjunction_count = sum(1 for word in self.conjunction_words if re.search(r'\b' + word + r'\b', command, re.IGNORECASE))
        conditional_count = sum(1 for word in self.conditional_words if re.search(r'\b' + word + r'\b', command, re.IGNORECASE))
        
        # Count distinct action verbs
        action_count = sum(1 for keyword in self.action_keywords if keyword in command)
        
        # Determine complexity
        if conditional_count > 0:
            return CommandComplexity.CONDITIONAL
        elif conjunction_count >= 2 or action_count >= 3:
            return CommandComplexity.WORKFLOW
        elif conjunction_count >= 1 or action_count >= 2:
            return CommandComplexity.COMPOUND
        else:
            return CommandComplexity.SIMPLE
    
    def _extract_context(self, command: str) -> Dict[str, Any]:
        """Extract context information from the command"""
        context = {
            'programming_languages': [],
            'tools': [],
            'file_types': [],
            'locations': [],
            'technologies': []
        }
        
        # Programming languages
        languages = ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift']
        for lang in languages:
            if lang in command:
                context['programming_languages'].append(lang)
        
        # Development tools
        tools = ['vscode', 'git', 'npm', 'pip', 'docker', 'nodejs', 'react', 'angular', 'vue']
        for tool in tools:
            if tool in command:
                context['tools'].append(tool)
        
        # File types
        file_types = ['.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.txt', '.md']
        for ft in file_types:
            if ft in command:
                context['file_types'].append(ft)
        
        # Common locations
        locations = ['desktop', 'documents', 'downloads', 'home', 'project', 'workspace']
        for loc in locations:
            if loc in command:
                context['locations'].append(loc)
        
        return context
    
    def _parse_workflow_command(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Parse complex workflow commands"""
        steps = []
        
        # Check for loop/iteration constructs (NEW - more versatile)
        if self._has_loop_construct(command):
            return self._parse_loop_command(command, context)
        
        # Check for nested operations
        if self._has_nested_operations(command):
            return self._parse_nested_command(command, context)
        
        # Check for common workflow patterns
        if 'web scraping' in command or 'scrape' in command:
            steps.extend(self._create_web_scraping_workflow(command, context))
        elif 'development environment' in command or 'dev environment' in command:
            steps.extend(self._create_dev_environment_workflow(command, context))
        elif 'data analysis' in command or ('pandas' in command and ('matplotlib' in command or 'seaborn' in command)):
            steps.extend(self._create_data_analysis_workflow(command, context))
        elif 'backup' in command and ('download' in command or 'install' in command):
            steps.extend(self._create_backup_and_install_workflow(command, context))
        elif 'project' in command and any(lang in command for lang in context['programming_languages']):
            steps.extend(self._create_project_setup_workflow(command, context))
        else:
            # Generic workflow parsing
            steps.extend(self._parse_generic_workflow(command))
        
        return steps
    
    def _create_web_scraping_workflow(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Create workflow for web scraping projects"""
        steps = []
        
        # Extract project name
        project_match = re.search(r'(?:project|folder)\s+(?:called\s+)?[\'"]?([^\'"]+)[\'"]?', command)
        project_name = project_match.group(1) if project_match else 'WebScrapingProject'
        
        # Step 1: Create project structure
        steps.append(ParsedStep(
            action='create_web_scraping_project',
            category='project_generator',
            params={'name': project_name, 'type': 'web_scraping'},
            priority=1
        ))
        
        # Step 2: Install dependencies
        if 'requests' in command or 'beautifulsoup' in command:
            steps.append(ParsedStep(
                action='install_packages',
                category='package_manager',
                params={'packages': ['requests', 'beautifulsoup4', 'lxml']},
                dependencies=[0],
                priority=2
            ))
        
        # Step 3: Create scraper file
        if 'news' in command or 'headlines' in command:
            steps.append(ParsedStep(
                action='create_news_scraper',
                category='code_generator',
                params={'filename': 'news_scraper.py', 'target': 'headlines'},
                dependencies=[0, 1],
                priority=3
            ))
        
        # Step 4: Open in editor
        if 'vscode' in command or 'vs code' in command:
            steps.append(ParsedStep(
                action='open_in_vscode',
                category='editor',
                params={'path': project_name},
                dependencies=[0, 1, 2],
                priority=4
            ))
        
        return steps
    
    def _create_dev_environment_workflow(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Create development environment setup workflow"""
        steps = []
        
        # Install Git
        if 'git' in command:
            steps.append(ParsedStep(
                action='install_git',
                category='installer',
                params={'silent': True},
                priority=1
            ))
        
        # Install Node.js
        if 'nodejs' in command or 'node.js' in command or 'npm' in command:
            steps.append(ParsedStep(
                action='install_nodejs',
                category='installer',
                params={'version': 'latest'},
                priority=2
            ))
        
        # Install VS Code
        if 'vscode' in command or 'vs code' in command:
            steps.append(ParsedStep(
                action='install_vscode',
                category='installer',
                params={'extensions': ['python', 'javascript']},
                priority=3
            ))
        
        # Clone repository
        if 'clone' in command and 'repo' in command:
            repo_match = re.search(r'github\.com/([^/]+/[^/\s]+)', command)
            if repo_match:
                steps.append(ParsedStep(
                    action='clone_repository',
                    category='git',
                    params={'url': f'https://github.com/{repo_match.group(1)}'},
                    dependencies=[0] if 'git' in command else [],
                    priority=4
                ))
        
        # Start dev server
        if 'start' in command and ('server' in command or 'dev' in command):
            steps.append(ParsedStep(
                action='start_dev_server',
                category='development',
                params={'command': 'npm start'},
                dependencies=list(range(len(steps))),
                priority=5
            ))
        
        return steps
    
    def _create_backup_and_install_workflow(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Create backup and installation workflow"""
        steps = []
        
        # Create backup
        if 'backup' in command:
            if 'documents' in command:
                steps.append(ParsedStep(
                    action='backup_folder',
                    category='backup',
                    params={'source': 'Documents', 'destination': 'Backup_Documents'},
                    priority=1
                ))
        
        # Download installer
        if 'download' in command and 'python' in command:
            steps.append(ParsedStep(
                action='download_python_installer',
                category='downloader',
                params={'version': 'latest'},
                priority=2
            ))
        
        # Take screenshot when done
        if 'screenshot' in command:
            steps.append(ParsedStep(
                action='take_screenshot',
                category='gui',
                params={'filename': 'workflow_complete.png'},
                dependencies=list(range(len(steps))),
                priority=99
            ))
        
        return steps
    
    def _create_project_setup_workflow(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Create project setup workflow"""
        steps = []
        
        # Determine project type from context
        if 'python' in context['programming_languages']:
            project_type = 'python'
        elif 'javascript' in context['programming_languages']:
            project_type = 'javascript'
        else:
            project_type = 'generic'
        
        # Extract project name
        project_match = re.search(r'(?:project|folder)\s+[\'"]?([^\'"]+)[\'"]?', command)
        project_name = project_match.group(1) if project_match else 'MyProject'
        
        # Create project
        steps.append(ParsedStep(
            action=f'create_{project_type}_project',
            category='project_generator',
            params={'name': project_name},
            priority=1
        ))
        
        return steps
    
    def _create_data_analysis_workflow(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Create workflow for data analysis projects"""
        steps = []
        
        # Extract project name
        project_match = re.search(r'(?:project|analysis)\s+(?:called\s+)?[\'"]?([^\'"]+)[\'"]?', command)
        project_name = project_match.group(1) if project_match else 'DataAnalysisProject'
        
        # Step 1: Create data analysis project structure
        steps.append(ParsedStep(
            action='create_data_analysis_project',
            category='project_generator',
            params={'name': project_name, 'type': 'data_analysis'},
            priority=1
        ))
        
        # Step 2: Install data science packages
        packages = ['pandas', 'numpy', 'matplotlib', 'seaborn', 'jupyter']
        if 'scipy' in command:
            packages.append('scipy')
        if 'plotly' in command:
            packages.append('plotly')
        if 'sklearn' in command or 'scikit-learn' in command:
            packages.append('scikit-learn')
        
        steps.append(ParsedStep(
            action='install_packages',
            category='package_manager',
            params={'packages': packages},
            dependencies=[0],
            priority=2
        ))
        
        # Step 3: Generate sample data if requested
        if 'sample' in command or 'generate' in command:
            steps.append(ParsedStep(
                action='generate_sample_data',
                category='data_generator',
                params={'project_name': project_name},
                dependencies=[0],
                priority=3
            ))
        
        return steps
    
    def _parse_compound_command(self, command: str) -> List[ParsedStep]:
        """Parse compound commands with multiple actions"""
        steps = []
        
        # Split by conjunctions
        parts = re.split(r'\s+(?:and|then|also|plus)\s+', command)
        
        for i, part in enumerate(parts):
            # Parse each part as a simple command
            simple_steps = self._parse_simple_command(part.strip())
            for step in simple_steps:
                step.priority = i + 1
                if i > 0:  # Add dependency on previous step
                    step.dependencies = [len(steps) - 1]
                steps.append(step)
        
        return steps
    
    def _parse_simple_command(self, command: str) -> List[ParsedStep]:
        """Parse simple single-action commands with smart NLP"""
        
        # Handle file modification: "modify p1.py from fibonacci to prime numbers"
        modify_match = re.search(r'modify\s+(\S+)\s+from\s+(\w+)\s+to\s+(\w+(?:\s+\w+)*)', command, re.IGNORECASE)
        if modify_match:
            file_path = modify_match.group(1)
            old_type = modify_match.group(2)
            new_type = modify_match.group(3)
            return [ParsedStep(
                action='modify_file',
                category='code_modification',
                params={'file_path': file_path, 'intent': f'convert {old_type} to {new_type}'},
                priority=1
            )]
        
        # Handle batch folder/file creation: "create 10 folders from project1 to project10"
        batch_folder_match = re.search(r'create\s+(\d+)\s+(?:folders?|directories?)\s+(?:(?:from|named)\s+)?(\w+)\s+to\s+(\w+)', command, re.IGNORECASE)
        if batch_folder_match:
            count = int(batch_folder_match.group(1))
            start_name = batch_folder_match.group(2)
            end_name = batch_folder_match.group(3)
            
            # Extract location if specified
            location_match = re.search(r'(?:on|in|at)\s+(\w+)', command, re.IGNORECASE)
            location = location_match.group(1) if location_match else None
            
            # Generate folder names
            start_num = self._extract_number(start_name)
            end_num = self._extract_number(end_name)
            base_start = self._extract_base_name(start_name)
            base_end = self._extract_base_name(end_name)
            
            # Use the common base name
            base_name = base_start if base_start == base_end else start_name
            
            steps = []
            if start_num is not None and end_num is not None:
                for i in range(start_num, end_num + 1):
                    folder_name = f"{base_name}{i}"
                    steps.append(ParsedStep(
                        action='create_folder',
                        category='filesystem',
                        params={'name': folder_name, 'location': location},
                        priority=i - start_num + 1
                    ))
            return steps if steps else [ParsedStep(
                action='unknown',
                category='unknown',
                params={'raw_command': command},
                priority=1
            )]
        
        # Handle simple copy/move/delete commands
        if 'copy' in command.lower():
            parts = command.lower().split(' to ')
            if len(parts) == 2:
                source = parts[0].replace('copy', '').strip()
                dest = parts[1].strip()
                return [ParsedStep(
                    action='copy',
                    category='filesystem',
                    params={'source': source, 'destination': dest},
                    priority=1
                )]
        
        if 'move' in command.lower():
            parts = command.lower().split(' to ')
            if len(parts) == 2:
                source = parts[0].replace('move', '').strip()
                dest = parts[1].strip()
                return [ParsedStep(
                    action='move',
                    category='filesystem',
                    params={'source': source, 'destination': dest},
                    priority=1
                )]
        
        # Handle folder creation
        if 'create' in command.lower() and ('folder' in command.lower() or 'directory' in command.lower()):
            folder_match = re.search(r'(?:folder|directory)\s+["\']?(\w+)["\']?', command, re.IGNORECASE)
            folder_name = folder_match.group(1) if folder_match else 'NewFolder'
            
            location_match = re.search(r'(?:on|in|at)\s+(\w+)', command, re.IGNORECASE)
            location = location_match.group(1) if location_match else None
            
            return [ParsedStep(
                action='create_folder',
                category='filesystem',
                params={'name': folder_name, 'location': location},
                priority=1
            )]
        
        # Default fallback
        return [ParsedStep(
            action='unknown',
            category='unknown',
            params={'raw_command': command},
            priority=1
        )]
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extract number from text like 'project1' -> 1"""
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None
    
    def _extract_base_name(self, text: str) -> str:
        """Extract base name from text like 'project1' -> 'project'"""
        return re.sub(r'\d+$', '', text)
    
    def _parse_conditional_command(self, command: str) -> List[ParsedStep]:
        """Parse conditional commands with if-then logic"""
        steps = []
        
        # Extract condition and action parts
        if_match = re.search(r'if\s+(.+?)\s+then\s+(.+)', command)
        when_match = re.search(r'when\s+(.+?)\s+(?:then\s+)?(.+)', command)
        
        if if_match:
            condition = if_match.group(1)
            action = if_match.group(2)
        elif when_match:
            condition = when_match.group(1)
            action = when_match.group(2)
        else:
            # Fallback to compound parsing
            return self._parse_compound_command(command)
        
        # Create conditional step
        action_steps = self._parse_simple_command(action)
        for step in action_steps:
            step.conditions = [condition]
            steps.append(step)
        
        return steps
    
    def _parse_generic_workflow(self, command: str) -> List[ParsedStep]:
        """Parse generic workflow commands"""
        # Split by conjunctions and create steps
        parts = re.split(r'\s+(?:and|then|after|next|also|plus|followed by)\s+', command)
        steps = []
        
        for i, part in enumerate(parts):
            simple_steps = self._parse_simple_command(part.strip())
            for step in simple_steps:
                step.priority = i + 1
                if i > 0:
                    step.dependencies = [len(steps) - 1]
                steps.append(step)
        
        return steps
    
    def _estimate_duration(self, steps: List[ParsedStep]) -> int:
        """Estimate execution duration in seconds"""
        duration_map = {
            'create_folder': 1,
            'create_file': 2,
            'install_packages': 30,
            'download_file': 60,
            'backup_folder': 120,
            'clone_repository': 45,
            'install_git': 180,
            'install_nodejs': 240,
            'install_vscode': 300
        }
        
        total_duration = 0
        for step in steps:
            total_duration += duration_map.get(step.action, 5)
        
        return total_duration
    
    def _load_workflow_patterns(self) -> Dict[str, List[str]]:
        """Load common workflow patterns"""
        return {
            'web_development': ['create project', 'install dependencies', 'setup server', 'open editor'],
            'data_science': ['create project', 'install packages', 'create notebook', 'load data'],
            'mobile_development': ['create project', 'setup sdk', 'create app', 'test device'],
            'devops': ['setup environment', 'configure tools', 'deploy application', 'monitor']
        }
    
    def _load_action_keywords(self) -> List[str]:
        """Load action keywords for complexity detection"""
        return [
            'create', 'make', 'build', 'generate', 'setup', 'install', 'download', 'upload',
            'copy', 'move', 'delete', 'remove', 'open', 'close', 'start', 'stop', 'run',
            'execute', 'launch', 'kill', 'terminate', 'backup', 'restore', 'sync', 'clone',
            'commit', 'push', 'pull', 'deploy', 'test', 'debug', 'compile', 'build'
        ]
    
    def _load_context_keywords(self) -> Dict[str, List[str]]:
        """Load context keywords for better understanding"""
        return {
            'development': ['project', 'code', 'programming', 'development', 'software'],
            'web': ['website', 'web', 'html', 'css', 'javascript', 'server', 'api'],
            'data': ['data', 'database', 'csv', 'json', 'analysis', 'visualization'],
            'system': ['system', 'admin', 'configuration', 'settings', 'registry'],
            'network': ['network', 'internet', 'download', 'upload', 'sync', 'cloud']
        }
    def _has_loop_construct(self, command: str) -> bool:
        """Check if command contains loop/iteration constructs"""
        loop_indicators = [
            r'\b\d+\s+folders?\b',  # "10 folders"
            r'create.*(?:each|every)\b',  # "create for each"
            r'(?:for|to)\s+\d+\s*(?:times?|iterations?)',  # "for 10 times"
            r'from.*to\s+\d+',  # "from 1 to 10"
            r'multiply|multiplication table',  # multiplication operations
            r'repeat|duplicate.*\d+',  # "repeat 5 times"
            r'\d+\s+(?:times?|copies|instances)',  # "5 times", "5 copies"
        ]
        
        for indicator in loop_indicators:
            if re.search(indicator, command, re.IGNORECASE):
                return True
        return False
    
    def _has_nested_operations(self, command: str) -> bool:
        """Check if command contains nested/hierarchical operations"""
        nested_indicators = [
            r'in\s+(?:that|those|each|every)',  # "in each folder"
            r'inside\s+(?:that|those|each)',  # "inside each"
            r'and\s+in\s+(?:those|each)',  # "and in each"
            r'with\s+(?:each|every)\s+(?:file|folder)',  # "with each file"
        ]
        
        for indicator in nested_indicators:
            if re.search(indicator, command, re.IGNORECASE):
                return True
        return False
    
    def _parse_loop_command(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Parse commands with loops/iterations - handles multi-level nesting intelligently"""
        steps = []
        import os
        
        try:
            # Extract the container/parent name
            container_match = re.search(r'create\s+(?:a\s+)?([a-zA-Z\s]+?)\s+folder(?:\s+and|$)', command, re.IGNORECASE)
            
            if container_match:
                container_name = container_match.group(1).strip()
                container_name = re.sub(r'^\s*(?:a|an|the)\s+', '', container_name, flags=re.IGNORECASE).strip()
            else:
                return self._fallback_parse_simple(command, context)
            
            # Extract location
            location_match = re.search(r'location\s+(?:of\s+the\s+main\s+folder\s+should\s+be\s+)?([A-Za-z]:\\[^\s"\']+)', command, re.IGNORECASE)
            location = location_match.group(1) if location_match else context.get('locations', [''])[0] if context.get('locations') else ''
            
            # Create main container
            steps.append(ParsedStep(
                action='create_folder',
                category='filesystem',
                params={'name': container_name, 'location': location if location else '.'},
                priority=1
            ))
            
            # Parse all nesting levels
            container_full_path = os.path.join(location, container_name) if location and location != '.' else container_name
            
            # Extract all "make ... folders" patterns with their corresponding items
            level1_items = self._extract_items_between_patterns(command, r'make\s+', r'\s+(?:folders?|directories?)\s+and\s+in\s+each')
            
            if not level1_items:
                # Try simpler pattern if first doesn't match
                level1_items = self._extract_items_between_patterns(command, r'make\s+', r'\s+(?:folders?|directories?)')
            
            if not level1_items:
                return self._fallback_parse_simple(command, context)
            
            # Process level 1 items
            for i, item1 in enumerate(level1_items, 1):
                # Create level 1 folder
                steps.append(ParsedStep(
                    action='create_folder',
                    category='filesystem',
                    params={'name': item1, 'parent': container_name, 'location': location if location else '.'},
                    priority=2
                ))
                
                # Find nested items for this level 1 item
                # Pattern: "in each <item1_type> make/create <items>"
                # Detect what type of item (service, folder, etc.)
                item1_type = self._infer_item_type(item1, level1_items, command)
                
                # Look for "in each <type> make X Y Z" patterns
                level2_patterns = re.finditer(
                    rf'in\s+each\s+(?:of\s+the\s+)?(?:\w+\s+)?(?:folder|directory|{re.escape(item1_type)})\s+(?:make|create)\s+([a-zA-Z0-9_\s]+?)\s+(?:(?:sub)?folders?|directories?)',
                    command,
                    re.IGNORECASE
                )
                
                level2_patterns_list = list(level2_patterns)
                
                if level2_patterns_list:
                    # Process each "in each" pattern
                    for pattern_match in level2_patterns_list:
                        level2_items = self._parse_item_list(pattern_match.group(1))
                        
                        for j, item2 in enumerate(level2_items, 1):
                            # Create level 2 folder
                            item1_full_path = os.path.join(container_full_path, item1) if location and location != '.' else item1
                            steps.append(ParsedStep(
                                action='create_folder',
                                category='filesystem',
                                params={'name': item2, 'parent': item1, 'location': item1_full_path},
                                priority=3
                            ))
                            
                            # Look for tertiary nesting (in each of the <item2> or <item2_plural>)
                            item2_plural = item2 + 's' if not item2.endswith('s') else item2
                            # Match "in each of the <item2_singular_or_plural> [optional: folders/directories] create ..."
                            level3_pattern = (
                                rf'in\s+each\s+of\s+the\s+(?:{re.escape(item2)}|{re.escape(item2_plural)})'
                                rf'(?:\s+(?:folders?|directories?))?\s+(?:make|create)\s+'
                                rf'([a-zA-Z0-9_\s]+?)\s+(?:(?:sub)?folders?|directories?)'
                            )
                            level3_match = re.search(level3_pattern, command, re.IGNORECASE)
                            
                            if level3_match:
                                level3_items = self._parse_item_list(level3_match.group(1))
                                
                                for k, item3 in enumerate(level3_items, 1):
                                    item2_full_path = os.path.join(item1_full_path, item2) if location and location != '.' else item2
                                    steps.append(ParsedStep(
                                        action='create_folder',
                                        category='filesystem',
                                        params={'name': item3, 'parent': item2, 'location': item2_full_path},
                                        priority=4
                                    ))
                
                # Handle special cases like "and then in resources make X Y Z"
                special_match = re.search(
                    rf'and\s+then\s+in\s+({re.escape(item1)})\s+make\s+([a-zA-Z0-9_\s]+?)\s+(?:(?:sub)?folders?|directories?)',
                    command,
                    re.IGNORECASE
                )
                
                if special_match:
                    special_items = self._parse_item_list(special_match.group(2))
                    item1_full_path = os.path.join(container_full_path, item1) if location and location != '.' else item1
                    
                    for m, special_item in enumerate(special_items, 1):
                        steps.append(ParsedStep(
                            action='create_folder',
                            category='filesystem',
                            params={'name': special_item, 'parent': item1, 'location': item1_full_path},
                            priority=3
                        ))
            
            # Generate config files if mentioned
            if 'test configuration' in command.lower() or 'config' in command.lower():
                steps.append(ParsedStep(
                    action='create_file',
                    category='filesystem',
                    params={
                        'name': 'test_config.json',
                        'content': self._generate_test_config(),
                        'parent': container_name
                    },
                    priority=5
                ))
            
            return steps
        
        except Exception as e:
            self.logger.warning(f"Complex nesting pattern failed: {e}. Using fallback parser.")
            return self._fallback_parse_complex(command, context)
    
    def _extract_items_between_patterns(self, command: str, start_pattern: str, end_pattern: str) -> List[str]:
        """Extract items between two regex patterns"""
        match = re.search(start_pattern + r'([a-zA-Z0-9_\s]+?)' + end_pattern, command, re.IGNORECASE)
        if match:
            return self._parse_item_list(match.group(1))
        return []
    
    def _parse_item_list(self, items_str: str) -> List[str]:
        """Parse a comma/and-separated list of items intelligently"""
        if not items_str or not items_str.strip():
            return []
        
        # Replace "and" with delimiter
        items_str = re.sub(r'\s+and\s+', '|', items_str, flags=re.IGNORECASE)
        # Split by whitespace and delimiter, remove articles
        items = re.split(r'[\s|]+', items_str)
        items = [item.strip() for item in items if item.strip() and item.lower() not in ['and', 'the', 'a', 'an']]
        return items
    
    def _infer_item_type(self, item: str, items: List[str], command: str) -> str:
        """Infer the type of item (service, test, component, etc.)"""
        # Check for common suffixes
        if item.endswith('_service'):
            return 'service'
        elif item.endswith('_tests'):
            return 'test'
        elif item.endswith('_folder'):
            return 'folder'
        elif item.endswith('_component'):
            return 'component'
        else:
            # Use a generic term
            return 'folder'
    
    def _fallback_parse_complex(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Fallback parser for commands that are too complex"""
        self.logger.warning("Command complexity exceeds supported nesting levels. Creating basic structure.")
        steps = []
        
        # Extract basic container name
        container_match = re.search(r'create\s+(?:a\s+)?([a-zA-Z\s]+?)\s+folder', command, re.IGNORECASE)
        container_name = container_match.group(1).strip() if container_match else 'project'
        container_name = re.sub(r'^\s*(?:a|an|the)\s+', '', container_name, flags=re.IGNORECASE).strip()
        
        # Extract location
        location_match = re.search(r'location\s+(?:of\s+the\s+main\s+folder\s+should\s+be\s+)?([A-Za-z]:\\[^\s"\']+)', command, re.IGNORECASE)
        location = location_match.group(1) if location_match else ''
        
        # Create container
        steps.append(ParsedStep(
            action='create_folder',
            category='filesystem',
            params={'name': container_name, 'location': location if location else '.'},
            priority=1
        ))
        
        return steps
    
    def _fallback_parse_simple(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Fallback parser for simple commands"""
        steps = []
        
        container_match = re.search(r'create\s+(?:a\s+)?([a-zA-Z\s]+?)\s+folder', command, re.IGNORECASE)
        container_name = container_match.group(1).strip() if container_match else 'project'
        
        location_match = re.search(r'location\s+(?:of\s+the\s+main\s+folder\s+should\s+be\s+)?([A-Za-z]:\\[^\s"\']+)', command, re.IGNORECASE)
        location = location_match.group(1) if location_match else ''
        
        steps.append(ParsedStep(
            action='create_folder',
            category='filesystem',
            params={'name': container_name, 'location': location if location else '.'},
            priority=1
        ))
        
        return steps
    
    def _generate_test_config(self) -> str:
        """Generate test configuration file content"""
        return """{
  "test_framework": "pytest",
  "test_runner": "python -m pytest",
  "coverage_enabled": true,
  "min_coverage": 80,
  "parallel_execution": true,
  "timeout_seconds": 300,
  "log_level": "INFO",
  "environment": "test"
}"""
    
    def _generate_master_registry(self, container: str, items: List[str], subitems: List[str]) -> str:
        """Generate master registry file"""
        lines = [
            "=" * 70,
            "MASTER TEST REGISTRY",
            "=" * 70,
            f"Test Framework: {container}",
            f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "TEST SUITES:",
            "-" * 70,
        ]
        
        for item in items:
            lines.append(f"\n[{item.upper()}]")
            lines.append(f"Location: {container}/{item}")
            lines.append(f"Description: {item.replace('_', ' ').title()} tests")
            
            if subitems:
                lines.append("Subfolders:")
                for subitem in subitems:
                    lines.append(f"  - {subitem}: {subitem.replace('_', ' ').title()}")
        
        lines.extend([
            "",
            "=" * 70,
            "Configuration: test_config.json",
            "=" * 70,
        ])
        
        return "\n".join(lines)
    
    def _parse_nested_command(self, command: str, context: Dict[str, Any]) -> List[ParsedStep]:
        """Parse commands with nested operations"""
        # This uses the loop parser since nested operations are usually within loops
        return self._parse_loop_command(command, context)
    
    def _generate_multiplication_table(self, number: int) -> str:
        """Generate multiplication table for a number"""
        lines = [f"Multiplication Table of {number}", "=" * 40]
        for i in range(1, 11):
            lines.append(f"{number} × {i} = {number * i}")
        return "\n".join(lines)