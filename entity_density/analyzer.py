"""Density scoring over plain text."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .dictionary import EntityDictionary
from .matching import find_candidates
from .normalization import normalize_text
from .selection import select_optimal


@dataclass(frozen=True)
class Mention:
    """A selected mention located in the normalized text."""

    entity_id: str
    alias: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class AnalysisResult:
    """Score plus the explainable mentions behind it."""

    score: int
    mentions: tuple[Mention, ...]
    normalized_text: str
    covered_characters: int
    total_characters: int


def analyze_text(dictionary: EntityDictionary, text: str) -> AnalysisResult:
    """Score ``text`` against a prepared dictionary.

    The score is ``floor(100 * covered / total)`` where ``covered`` is the
    number of letter/number characters covered by the selected mentions
    and ``total`` is the number of letter/number characters in the whole
    normalized text. A text without letters or digits scores 0.
    """
    normalized = normalize_text(text)
    total = sum(
        1 for char in normalized if unicodedata.category(char)[0] in ("L", "N")
    )

    candidates = find_candidates(dictionary, normalized)
    chosen = select_optimal(candidates, len(normalized))
    covered = sum(candidate.cover for candidate in chosen)

    score = (100 * covered) // total if total else 0
    mentions = tuple(
        Mention(
            entity_id=candidate.entity_id,
            alias=candidate.alias,
            start=candidate.start,
            end=candidate.end,
            text=normalized[candidate.start : candidate.end],
        )
        for candidate in chosen
    )
    return AnalysisResult(
        score=score,
        mentions=mentions,
        normalized_text=normalized,
        covered_characters=covered,
        total_characters=total,
    )
