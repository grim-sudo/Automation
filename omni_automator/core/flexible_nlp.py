#!/usr/bin/env python3
"""
Advanced Flexible NLP Processor
Handles natural language variations and syntactic flexibility
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class NLPVariation:
    """Natural language variation of a command"""
    original: str
    normalized: str
    synonyms: List[str]
    alternatives: List[str]
    flexibility_score: float


class FlexibleNLPProcessor:
    """Process natural language with flexibility for variations"""
    
    def __init__(self):
        # Synonym mappings for flexible understanding
        self.synonyms = {
            'create': ['make', 'build', 'generate', 'setup', 'construct', 'build', 'spawn', 'initialize'],
            'delete': ['remove', 'erase', 'destroy', 'discard', 'purge', 'eliminate', 'drop'],
            'copy': ['duplicate', 'clone', 'replicate', 'reproduce', 'backup', 'mirror'],
            'move': ['transfer', 'relocate', 'shift', 'transport', 'migrate', 'transit'],
            'deploy': ['release', 'publish', 'launch', 'put online', 'go live', 'ship'],
            'setup': ['initialize', 'configure', 'establish', 'prepare', 'arrange'],
            'pipeline': ['workflow', 'process', 'sequence', 'chain', 'flow'],
            'docker': ['container', 'containerize', 'dockerize'],
            'kubernetes': ['k8s', 'orchestrate', 'orchestration'],
            'machine learning': ['ml', 'ai', 'neural network', 'deep learning', 'predictive'],
            'database': ['db', 'data store', 'repository', 'schema'],
            'api': ['endpoint', 'service', 'interface', 'rest service'],
            'monitor': ['observe', 'track', 'watch', 'supervise', 'check'],
            'security': ['protection', 'safety', 'defense', 'hardening'],
            'backup': ['copy', 'replicate', 'save', 'archive'],
            'restore': ['recover', 'retrieve', 'bring back'],
            'optimize': ['improve', 'enhance', 'fine-tune', 'tune', 'speedup'],
            'migrate': ['move', 'transfer', 'port', 'convert'],
        }
        
        # Word order flexibility patterns
        self.flexible_patterns = [
            # Standard: verb noun1 preposition noun2
            # Flexible: noun1 verb preposition noun2 (name-first)
            # Flexible: verb preposition noun2 noun1
        ]
        
        # Intensity modifiers
        self.intensity_words = {
            'completely': 3, 'fully': 3, 'entire': 3,
            'all': 2, 'entire': 2, 'comprehensive': 2,
            'basic': 1, 'simple': 1, 'minimal': 1,
        }
        
        # Context keywords
        self.context_keywords = {
            'with': 'includes_features',
            'using': 'includes_technology',
            'for': 'purpose',
            'on': 'location',
            'in': 'location',
            'at': 'location',
            'from': 'source',
            'to': 'destination',
            'including': 'includes_features',
            'and': 'conjunction',
        }
    
    def normalize(self, text: str) -> str:
        """Normalize text for processing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove filler words
        filler_words = ['please', 'kindly', 'can you', 'could you', 'would you', 'will you',
                       'i need', 'i want', 'i wish', 'i would like', 'hey', 'hello', 'hi',
                       'ok', 'okay', 'alright', 'just']
        
        for filler in filler_words:
            text = re.sub(rf'^\s*{filler}\s+', '', text, flags=re.IGNORECASE)
        
        # Convert to lowercase for processing
        return text.lower()
    
    def extract_synonyms(self, text: str) -> Dict[str, str]:
        """Extract and map synonyms in text"""
        text_lower = text.lower()
        matched_synonyms = {}
        
        for primary, syn_list in self.synonyms.items():
            # Check for primary word
            if primary in text_lower:
                matched_synonyms[primary] = primary
            
            # Check for synonyms
            for synonym in syn_list:
                if synonym in text_lower:
                    matched_synonyms[primary] = synonym
        
        return matched_synonyms
    
    def find_word_order_variations(self, text: str) -> List[str]:
        """Find alternative word orders in text"""
        variations = [text]
        words = text.split()
        
        # Try different word orderings for flexible matching
        if len(words) >= 3:
            # Original: verb noun1 to noun2
            # Variation 1: noun1 verb to noun2
            # Variation 2: to noun2 verb noun1
            
            # Find action words (verbs) and reorder
            action_words = ['create', 'make', 'setup', 'deploy', 'copy', 'move', 'delete']
            
            for action in action_words:
                if action in text:
                    # Move action word to different positions
                    without_action = ' '.join(w for w in words if w != action)
                    if without_action:
                        # Action at start (original)
                        # Action in middle
                        parts = without_action.split()
                        if len(parts) >= 2:
                            variations.append(f"{parts[0]} {action} {' '.join(parts[1:])}")
        
        return variations
    
    def extract_parameters_flexible(self, text: str) -> Dict[str, Any]:
        """Flexibly extract parameters from text"""
        params = {}
        text_lower = text.lower()
        
        # Extract numbers (counts, versions, etc.)
        numbers = re.findall(r'\d+', text)
        if numbers:
            params['count'] = int(numbers[0])
            params['numbers'] = [int(n) for n in numbers]
        
        # Extract filenames/paths
        file_patterns = [
            r'(?:file|folder|directory)?\s+([a-zA-Z0-9_\-\.]+(?:\.[a-zA-Z0-9]+)?)',
            r'(?:named|called)?\s+([a-zA-Z0-9_\-]+)',
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                params['name'] = matches[0]
                break
        
        # Extract locations
        locations = ['desktop', 'documents', 'downloads', 'pictures', 'music',
                    'videos', 'home', 'root', 'current', 'temp', 'tmp']
        for loc in locations:
            if loc in text_lower:
                params['location'] = loc
                break
        
        # Extract framework/language keywords
        frameworks = ['react', 'vue', 'angular', 'django', 'flask', 'nodejs',
                     'java', 'python', 'rust', 'go', 'csharp', 'cpp',
                     'tensorflow', 'pytorch', 'keras', 'scikit', 'pandas']
        
        matched_frameworks = [f for f in frameworks if f in text_lower]
        if matched_frameworks:
            params['frameworks'] = matched_frameworks
            params['primary_framework'] = matched_frameworks[0]
        
        # Extract features
        features_pattern = r'(?:with|including|and|featuring)\s+([a-zA-Z0-9\s,\-]+?)(?:\s+(?:and|or|with|including)|$)'
        matches = re.findall(features_pattern, text_lower)
        if matches:
            params['features'] = [f.strip() for f in matches[0].split(',')]
        
        # Extract source and destination
        if 'from' in text_lower and 'to' in text_lower:
            from_match = re.search(r'from\s+([a-zA-Z0-9_\-\.]+)', text_lower)
            to_match = re.search(r'to\s+([a-zA-Z0-9_\-\.]+)', text_lower)
            
            if from_match:
                params['source'] = from_match.group(1)
            if to_match:
                params['destination'] = to_match.group(1)
        
        return params
    
    def measure_flexibility(self, original: str, normalized: str) -> float:
        """Measure how flexible the parsing was"""
        # Score based on how much normalization was needed
        similarity = len(set(original.split()) & set(normalized.split())) / len(set(original.split()) | set(normalized.split()))
        return similarity
    
    def process_flexible(self, text: str) -> NLPVariation:
        """Process text with maximum flexibility"""
        normalized = self.normalize(text)
        
        # Extract synonyms
        synonyms = list(self.extract_synonyms(text).values())
        
        # Find word order variations
        alternatives = self.find_word_order_variations(normalized)
        
        # Measure flexibility
        flexibility_score = self.measure_flexibility(text, normalized)
        
        return NLPVariation(
            original=text,
            normalized=normalized,
            synonyms=synonyms,
            alternatives=alternatives,
            flexibility_score=flexibility_score
        )
    
    def find_best_match(self, text: str, patterns: List[str]) -> Tuple[str, float]:
        """Find the best matching pattern for text with flexibility"""
        nlp_var = self.process_flexible(text)
        
        best_pattern = None
        best_score = 0
        
        # Try original
        for pattern in patterns:
            score = self._calculate_match_score(nlp_var.normalized, pattern)
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        # Try alternatives
        for alt in nlp_var.alternatives:
            for pattern in patterns:
                score = self._calculate_match_score(alt, pattern)
                if score > best_score:
                    best_score = score
                    best_pattern = pattern
        
        return best_pattern, best_score
    
    def _calculate_match_score(self, text: str, pattern: str) -> float:
        """Calculate similarity score between text and pattern"""
        text_words = set(text.split())
        pattern_words = set(pattern.split())
        
        if not text_words or not pattern_words:
            return 0.0
        
        intersection = len(text_words & pattern_words)
        union = len(text_words | pattern_words)
        
        return intersection / union if union > 0 else 0.0


# Singleton instance
_nlp_processor = FlexibleNLPProcessor()


def get_nlp_processor() -> FlexibleNLPProcessor:
    """Get NLP processor instance"""
    return _nlp_processor
