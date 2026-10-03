"""Entity density scoring for content analysis.

Prepare an entity dictionary once, then analyze plain text to get a
density score plus explainable entity mentions located in the
normalized text.
"""

from entity_density.dictionary import EntityDictionary
from entity_density.analyzer import Mention, AnalysisResult, analyze

__all__ = [
    "EntityDictionary",
    "Mention",
    "AnalysisResult",
    "analyze",
]
