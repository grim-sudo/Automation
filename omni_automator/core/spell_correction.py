#!/usr/bin/env python3
"""
Spell Correction & Typo Tolerance Module for OmniAutomator
Handles fuzzy matching for commands, keywords, and user input
Uses Levenshtein distance and fuzzy matching
"""

import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher, get_close_matches
from ..utils.logger import get_logger


class SpellCorrector:
    """Intelligent spell correction with fuzzy matching"""
    
    def __init__(self):
        self.logger = get_logger("SpellCorrector")
        
        # Command keywords and their variations
        self.command_keywords = {
            'create': ['create', 'make', 'generate', 'build', 'setup', 'initialize', 'new', 'mkdri'],
            'delete': ['delete', 'remove', 'rm', 'erase', 'destroy', 'eliminate', 'delet', 'dlete'],
            'copy': ['copy', 'duplicate', 'cp', 'clone', 'copi', 'copu'],
            'move': ['move', 'mv', 'transfer', 'relocate', 'moev', 'muve'],
            'rename': ['rename', 'rn', 'renam', 'renme'],
            'folder': ['folder', 'directory', 'dir', 'fodler', 'foldr', 'foldер', 'dir'],
            'file': ['file', 'document', 'doc', 'flie', 'fil'],
            'project': ['project', 'proj', 'projeect', 'prject'],
            'test': ['test', 'testing', 'tst', 'tess', 'tesst'],
            'run': ['run', 'execute', 'start', 'launch', 'exec', 'rn', 'runn'],
            'install': ['install', 'setup', 'add', 'instal', 'instll'],
            'download': ['download', 'fetch', 'get', 'pull', 'dwld', 'downlaod'],
            'upload': ['upload', 'push', 'send', 'upld', 'uplod'],
            'web': ['web', 'website', 'www', 'weeb', 'wbe'],
            'automation': ['automation', 'automate', 'auto', 'automtion', 'automatoin'],
            'script': ['script', 'code', 'program', 'scirpt', 'skript'],
            'configure': ['configure', 'config', 'setup', 'cfg', 'configue', 'configre'],
            'monitor': ['monitor', 'watch', 'track', 'moniter', 'montior'],
        }
        
        # Flatten the dictionary for reverse lookup
        self.keyword_to_canonical = {}
        for canonical, variations in self.command_keywords.items():
            for variation in variations:
                self.keyword_to_canonical[variation.lower()] = canonical
    
    def correct_text(self, text: str, threshold: float = 0.8) -> str:
        """
        Correct typos and grammatical errors in text
        
        Args:
            text: Input text to correct
            threshold: Fuzzy match threshold (0-1)
            
        Returns:
            Corrected text
        """
        words = text.split()
        corrected = []
        
        for word in words:
            # Try to find canonical form for this word
            corrected_word = self._correct_word(word, threshold)
            corrected.append(corrected_word)
        
        return ' '.join(corrected)
    
    def _correct_word(self, word: str, threshold: float) -> str:
        """Correct a single word"""
        word_lower = word.lower()
        
        # Exact match
        if word_lower in self.keyword_to_canonical:
            canonical = self.keyword_to_canonical[word_lower]
            # Preserve case
            if word.isupper():
                return canonical.upper()
            elif word[0].isupper():
                return canonical.capitalize()
            return canonical
        
        # Fuzzy match
        matches = get_close_matches(word_lower, self.keyword_to_canonical.keys(), n=1, cutoff=threshold)
        if matches:
            canonical = self.keyword_to_canonical[matches[0]]
            if word.isupper():
                return canonical.upper()
            elif word[0].isupper():
                return canonical.capitalize()
            return canonical
        
        return word
    
    def extract_keywords(self, text: str) -> Dict[str, str]:
        """
        Extract and correct keywords from text
        
        Returns:
            Dictionary mapping keyword types to corrected values
        """
        keywords = {}
        words = text.lower().split()
        
        for word in words:
            if word in self.keyword_to_canonical:
                canonical = self.keyword_to_canonical[word]
                keywords[canonical] = word
        
        return keywords
    
    def find_closest_match(self, word: str, candidates: List[str], threshold: float = 0.7) -> Optional[str]:
        """Find closest match from a list of candidates"""
        matches = get_close_matches(word, candidates, n=1, cutoff=threshold)
        return matches[0] if matches else None
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity score between two strings (0-1)"""
        distance = self.levenshtein_distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        return 1 - (distance / max_len) if max_len > 0 else 1.0
    
    def handle_typo_command(self, user_input: str, known_commands: List[str], threshold: float = 0.75) -> Optional[Tuple[str, float]]:
        """
        Find the closest command if user input has typos
        
        Returns:
            Tuple of (corrected_command, confidence_score) or None
        """
        best_match = None
        best_score = 0
        
        for command in known_commands:
            score = self.similarity_score(user_input, command)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = command
        
        return (best_match, best_score) if best_match else None
    
    def suggest_command_fixes(self, user_input: str, known_commands: List[str], top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Suggest multiple command fixes
        
        Returns:
            List of (command, score) tuples sorted by score
        """
        suggestions = []
        
        for command in known_commands:
            score = self.similarity_score(user_input, command)
            if score > 0.5:  # Only include reasonable matches
                suggestions.append((command, score))
        
        return sorted(suggestions, key=lambda x: x[1], reverse=True)[:top_n]


# Global instance
_spell_corrector = None


def get_spell_corrector() -> SpellCorrector:
    """Get or create global spell corrector instance"""
    global _spell_corrector
    if _spell_corrector is None:
        _spell_corrector = SpellCorrector()
    return _spell_corrector
