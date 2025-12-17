#!/usr/bin/env python3
"""
Advanced Semantic NLP Engine for OmniAutomator
Claude-level natural language understanding with semantic analysis
Provides deep intent recognition, context awareness, and sophisticated parsing
"""

import re
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
from ..utils.logger import get_logger


class IntentType(Enum):
    """High-level intent categories"""
    CREATE = "create"
    DELETE = "delete"
    MODIFY = "modify"
    QUERY = "query"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    ANALYZE = "analyze"
    HELP = "help"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Entity types in natural language"""
    FILE = "file"
    FOLDER = "folder"
    PROJECT = "project"
    PROCESS = "process"
    PATH = "path"
    URL = "url"
    COMMAND = "command"
    PARAMETER = "parameter"
    TIME_DURATION = "time_duration"
    QUANTITY = "quantity"


@dataclass
class SemanticToken:
    """Semantic representation of a token"""
    text: str
    entity_type: EntityType
    confidence: float
    original_text: str
    semantic_value: Any = None


@dataclass
class SemanticAnalysis:
    """Complete semantic analysis result"""
    original_text: str
    corrected_text: str
    intent: IntentType
    confidence: float
    entities: List[SemanticToken]
    parameters: Dict[str, Any]
    context_requirements: List[str]
    ambiguities: List[str]
    suggestions: List[str]


class SemanticNLPEngine:
    """
    Powerful semantic NLP engine with Claude-level understanding
    Provides:
    - Deep semantic analysis
    - Intent recognition
    - Entity extraction
    - Context awareness
    - Ambiguity resolution
    - Multi-level interpretation
    """
    
    def __init__(self):
        self.logger = get_logger("SemanticNLP")
        
        # Intent patterns with context sensitivity
        self.intent_patterns = {
            IntentType.CREATE: [
                r'\b(create|make|new|build|generate|setup|initialize|scaffold)\b',
                r'\b(generate|produce|construct|spawn|instantiate)\b',
                r'mkdir|mkdri'
            ],
            IntentType.DELETE: [
                r'\b(delete|remove|rm|erase|destroy|eliminate|purge|delet)\b',
                r'\b(wipe|clear|uninstall)\b'
            ],
            IntentType.MODIFY: [
                r'\b(modify|update|change|alter|edit|rename|move|copy|duplicate)\b',
                r'\b(transform|convert|adapt)\b'
            ],
            IntentType.QUERY: [
                r'\b(show|list|get|find|search|look|display|view)\b',
                r'\b(check|verify|confirm|status)\b'
            ],
            IntentType.EXECUTE: [
                r'\b(run|execute|start|launch|begin|trigger|invoke)\b',
                r'\b(call|perform|do)\b'
            ],
            IntentType.CONFIGURE: [
                r'\b(configure|setup|config|set|adjust|tune|optimize)\b',
                r'\b(enable|disable|activate)\b'
            ],
            IntentType.ANALYZE: [
                r'\b(analyze|examine|inspect|review|audit)\b',
                r'\b(evaluate|assess|measure)\b'
            ]
        }
        
        # Entity patterns
        self.entity_patterns = {
            EntityType.FILE: [
                r'\.(\w+)\b',  # file.ext
                r'(?:file|doc|script|code)\s+(?:called|named|is|called)\s+"?([^"\s]+)"?'
            ],
            EntityType.FOLDER: [
                r'(?:folder|dir|directory|path)\s+(?:called|named|is)\s+"?([^"\s]+)"?',
                r'(?:in|at|under)\s+(\S+(?:/\S+)*)'
            ],
            EntityType.PATH: [
                r'(?:C:|~|/)[\\\/]?(?:[\w\-]+[\\\/])*[\w\-]*',
                r'(?:home|desktop|documents|downloads|projects)(?:/[\w\-]+)*'
            ],
            EntityType.PROJECT: [
                r'(?:project|app|application|system|module)\s+(?:called|named|is)\s+"?([^"\s]+)"?'
            ],
            EntityType.QUANTITY: [
                r'(\d+)\s+(?:folders?|files?|items?|things?)',
                r'(?:one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand)\s+(?:folders?|items?)'
            ]
        }
        
        # Semantic relationship mappings
        self.semantic_relations = {
            'containment': ['in', 'inside', 'within', 'under'],
            'destination': ['to', 'into', 'towards'],
            'source': ['from', 'of', 'out of'],
            'modification': ['with', 'using', 'via', 'through'],
            'quantity': ['of', 'with'],
            'timing': ['before', 'after', 'when', 'as']
        }
        
        # Contextual ambiguity resolvers
        self.ambiguity_resolvers = {
            'test': ['testing folder', 'test data', 'test script'],
            'run': ['execute', 'operate', 'start'],
            'make': ['create', 'build', 'construct']
        }
    
    def analyze(self, text: str) -> SemanticAnalysis:
        """
        Perform comprehensive semantic analysis
        
        Returns:
            SemanticAnalysis with complete interpretation
        """
        original = text
        corrected = text
        intent = self._determine_intent(text)
        entities = self._extract_entities(text)
        parameters = self._extract_parameters(text, entities)
        context_requirements = self._identify_context_requirements(intent, entities)
        ambiguities = self._detect_ambiguities(text, intent)
        suggestions = self._generate_suggestions(intent, parameters, ambiguities)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(intent, entities, parameters)
        
        return SemanticAnalysis(
            original_text=original,
            corrected_text=corrected,
            intent=intent,
            confidence=confidence,
            entities=entities,
            parameters=parameters,
            context_requirements=context_requirements,
            ambiguities=ambiguities,
            suggestions=suggestions
        )
    
    def _determine_intent(self, text: str) -> IntentType:
        """Determine primary intent from text"""
        text_lower = text.lower()
        
        # Score each intent type
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            intent_scores[intent] = score
        
        # Find highest scoring intent
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)
        
        return IntentType.UNKNOWN
    
    def _extract_entities(self, text: str) -> List[SemanticToken]:
        """
        Extract semantic entities from text
        Identifies files, folders, paths, quantities, etc.
        """
        entities = []
        
        # Extract quantities
        quantity_matches = re.finditer(r'(\d+)\s+(?:folder|dir|file|item)s?', text, re.IGNORECASE)
        for match in quantity_matches:
            entities.append(SemanticToken(
                text=match.group(1),
                entity_type=EntityType.QUANTITY,
                confidence=0.95,
                original_text=match.group(0),
                semantic_value=int(match.group(1))
            ))
        
        # Extract file paths
        path_pattern = r'(?:[A-Z]:|~|\.)?(?:[\/\\][\w\-\.]+)*[\/\\]?[\w\-\.]+'
        path_matches = re.finditer(path_pattern, text)
        for match in path_matches:
            entities.append(SemanticToken(
                text=match.group(0),
                entity_type=EntityType.PATH,
                confidence=0.85,
                original_text=match.group(0)
            ))
        
        # Extract filenames
        file_pattern = r'[\w\-]+\.\w+'
        file_matches = re.finditer(file_pattern, text)
        for match in file_matches:
            entities.append(SemanticToken(
                text=match.group(0),
                entity_type=EntityType.FILE,
                confidence=0.90,
                original_text=match.group(0)
            ))
        
        # Extract folder/project names (in quotes or after keywords)
        named_pattern = r'(?:named|called|is)\s+"?([^"\s,]+)"?'
        named_matches = re.finditer(named_pattern, text, re.IGNORECASE)
        for match in named_matches:
            # Determine if file or folder based on context
            entity_type = EntityType.FOLDER if len(match.group(1).split('.')) == 1 else EntityType.FILE
            entities.append(SemanticToken(
                text=match.group(1),
                entity_type=entity_type,
                confidence=0.92,
                original_text=match.group(0)
            ))
        
        return entities
    
    def _extract_parameters(self, text: str, entities: List[SemanticToken]) -> Dict[str, Any]:
        """Extract structured parameters from text"""
        parameters = {}
        text_lower = text.lower()
        
        # Extract full file paths (e.g., C:\Users\shefa\Desktop, /home/user/path)
        full_path_pattern = r'(?:[A-Z]:\\[\w\s\-\\\.]+|/[\w\s\-/\.]+)'
        full_path_matches = re.finditer(full_path_pattern, text)
        for match in full_path_matches:
            path = match.group(0)
            if '\\' in path or path.startswith('/'):
                parameters['location'] = path
                parameters['destination'] = path
        
        # Extract location/path parameters from text patterns
        # Patterns like "in Desktop", "to C:\...", "as C:\..."
        location_patterns = [
            r'(?:in|into|to|at|destination|folder|path|location)\s+(?:as\s+)?(?:the\s+)?([A-Z]:[\\\/][\w\s\-\\\.]+|[\w\s\-\.]+)',
            r'(?:the\s+)?(?:folder\s+)?destination\s+(?:as|is)\s+([A-Z]:[\\\/][\w\s\-\\\.]+)',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location:
                    parameters['location'] = location
                    parameters['destination'] = location
        
        # Extract naming parameters
        for entity in entities:
            if entity.entity_type in [EntityType.FILE, EntityType.FOLDER, EntityType.PROJECT]:
                parameters['name'] = entity.text
        
        # Extract quantity parameters
        for entity in entities:
            if entity.entity_type == EntityType.QUANTITY:
                parameters['quantity'] = entity.semantic_value
        
        # Extract range parameters (test1 to test100)
        range_pattern = r'(?:from|to)\s+(\w+)(\d+)\s+(?:to|through)\s+(\w+)(\d+)'
        range_match = re.search(range_pattern, text, re.IGNORECASE)
        if range_match:
            parameters['range_start'] = int(range_match.group(2))
            parameters['range_end'] = int(range_match.group(4))
            parameters['range_prefix'] = range_match.group(1)
        
        return parameters
    
    def _identify_context_requirements(self, intent: IntentType, entities: List[SemanticToken]) -> List[str]:
        """Identify what context/information is needed"""
        requirements = []
        
        if intent in [IntentType.CREATE, IntentType.DELETE]:
            if not any(e.entity_type in [EntityType.FILE, EntityType.FOLDER] for e in entities):
                requirements.append("target_name")
            if not any(e.entity_type == EntityType.PATH for e in entities):
                requirements.append("target_location")
        
        if intent == IntentType.DELETE:
            requirements.append("confirmation")
        
        if intent == IntentType.EXECUTE:
            if not any(e.entity_type == EntityType.COMMAND for e in entities):
                requirements.append("command_name")
        
        return requirements
    
    def _detect_ambiguities(self, text: str, intent: IntentType) -> List[str]:
        """Detect potential ambiguities or unclear elements"""
        ambiguities = []
        
        # Check for pronouns without clear antecedent
        if re.search(r'\b(it|them|that|this)\b', text, re.IGNORECASE):
            if 'location' not in text.lower() and 'path' not in text.lower():
                ambiguities.append("unclear_target_reference")
        
        # Check for multiple possible interpretations
        if 'test' in text.lower():
            ambiguities.append("test_folder_or_test_data")
        
        # Check for missing parameters
        if intent == IntentType.CREATE and 'in' not in text.lower():
            ambiguities.append("missing_target_location")
        
        return ambiguities
    
    def _generate_suggestions(self, intent: IntentType, parameters: Dict[str, Any], 
                             ambiguities: List[str]) -> List[str]:
        """Generate helpful suggestions for the user"""
        suggestions = []
        
        # Suggest clarification for ambiguities
        for ambiguity in ambiguities:
            if ambiguity == "unclear_target_reference":
                suggestions.append("Please specify which folder you're referring to")
            elif ambiguity == "test_folder_or_test_data":
                suggestions.append("Did you mean a 'test' folder or test data?")
            elif ambiguity == "missing_target_location":
                suggestions.append("Where should I create this? (Desktop, Documents, or specific path)")
        
        # Suggest related operations
        if intent == IntentType.CREATE:
            suggestions.append("Would you like to add nested folders?")
        
        if intent == IntentType.DELETE:
            suggestions.append("Would you like to backup before deleting?")
        
        return suggestions
    
    def _calculate_confidence(self, intent: IntentType, entities: List[SemanticToken], 
                             parameters: Dict[str, Any]) -> float:
        """Calculate overall confidence in interpretation"""
        confidence = 0.5  # Base confidence
        
        # Boost for clear intent
        if intent != IntentType.UNKNOWN:
            confidence += 0.2
        
        # Boost for extracted entities
        confidence += min(0.2, len(entities) * 0.05)
        
        # Boost for complete parameters
        confidence += min(0.1, len(parameters) * 0.03)
        
        # Confidence from entity confidence scores
        if entities:
            avg_entity_confidence = sum(e.confidence for e in entities) / len(entities)
            confidence += avg_entity_confidence * 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def resolve_ambiguity(self, ambiguity: str, options: List[str], user_choice: int = 0) -> str:
        """Resolve detected ambiguity"""
        if 0 <= user_choice < len(options):
            return options[user_choice]
        return options[0] if options else ""
    
    def generate_clarification_question(self, ambiguity: str) -> str:
        """Generate natural clarification question"""
        questions = {
            'unclear_target_reference': "Which folder or file are you referring to?",
            'test_folder_or_test_data': "Did you mean to work with a 'test' folder or test data?",
            'missing_target_location': "Where would you like me to create this?",
            'missing_command': "What command should I execute?"
        }
        return questions.get(ambiguity, "Could you clarify this?")
    
    def understand_context(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Understand context from conversation history
        Provides multi-turn conversation awareness
        """
        context = {
            'last_intent': None,
            'last_target': None,
            'last_location': None,
            'conversation_topics': [],
            'established_facts': []
        }
        
        for exchange in conversation_history[-5:]:  # Look at last 5 exchanges
            user_msg = exchange.get('user', '')
            bot_response = exchange.get('bot', '')
            
            # Analyze user message for intent
            analysis = self.analyze(user_msg)
            context['last_intent'] = analysis.intent
            
            # Extract established targets and locations
            if analysis.parameters.get('name'):
                context['last_target'] = analysis.parameters['name']
            if analysis.parameters.get('location'):
                context['last_location'] = analysis.parameters['location']
            
            # Track conversation topics
            if analysis.intent != IntentType.UNKNOWN:
                context['conversation_topics'].append(analysis.intent.value)
        
        return context


# Global instance
_semantic_nlp = None


def get_semantic_nlp() -> SemanticNLPEngine:
    """Get or create global semantic NLP engine"""
    global _semantic_nlp
    if _semantic_nlp is None:
        _semantic_nlp = SemanticNLPEngine()
    return _semantic_nlp
