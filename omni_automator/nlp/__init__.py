"""
Natural Language Processing Module
Handles semantic analysis, flexible processing, and spell correction
"""

from .semantic_engine import SemanticNLPEngine, IntentType, EntityType, SemanticAnalysis, get_semantic_nlp
from .flexible_processor import FlexibleNLPProcessor, NLPVariation, get_nlp_processor
from .spell_corrector import SpellCorrector, get_spell_corrector

__all__ = [
    'SemanticNLPEngine',
    'IntentType',
    'EntityType',
    'SemanticAnalysis',
    'get_semantic_nlp',
    'FlexibleNLPProcessor',
    'NLPVariation',
    'get_nlp_processor',
    'SpellCorrector',
    'get_spell_corrector',
]
