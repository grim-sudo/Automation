"""
Natural Language Processing Module
Handles semantic analysis, flexible processing, and spell correction
"""

from .flexible_processor import FlexibleNLPProcessor, NLPVariation, get_nlp_processor
from .semantic_engine import (
    EntityType,
    IntentType,
    SemanticAnalysis,
    SemanticNLPEngine,
    get_semantic_nlp,
)
from .spell_corrector import SpellCorrector, get_spell_corrector

__all__ = [
    "SemanticNLPEngine",
    "IntentType",
    "EntityType",
    "SemanticAnalysis",
    "get_semantic_nlp",
    "FlexibleNLPProcessor",
    "NLPVariation",
    "get_nlp_processor",
    "SpellCorrector",
    "get_spell_corrector",
]
