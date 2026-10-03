"""Candidate mention detection in normalized text."""

from __future__ import annotations

import string
import unicodedata
from dataclasses import dataclass

from .dictionary import EntityDictionary

_WORD_CHARS = frozenset(string.ascii_letters + string.digits + "_")


def _is_word_char(char: str) -> bool:
    return char in _WORD_CHARS


def _count_letters_and_digits(text: str) -> int:
    return sum(1 for char in text if unicodedata.category(char)[0] in ("L", "N"))


def _boundaries_ok(normalized_text: str, alias: str, start: int, end: int) -> bool:
    if _is_word_char(alias[0]) and start > 0 and _is_word_char(normalized_text[start - 1]):
        return False
    if _is_word_char(alias[-1]) and end < len(normalized_text) and _is_word_char(
        normalized_text[end]
    ):
        return False
    return True


@dataclass(frozen=True)
class CandidateMention:
    """One occurrence of an alias in the normalized text."""

    entity_id: str
    alias: str
    start: int
    end: int
    cover: int


def find_candidates(dictionary: EntityDictionary, normalized_text: str) -> list[CandidateMention]:
    """Find all alias occurrences that satisfy the boundary rules."""
    candidates: list[CandidateMention] = []
    for entity in dictionary.entities:
        for alias in entity.aliases:
            position = normalized_text.find(alias)
            while position != -1:
                end = position + len(alias)
                if _boundaries_ok(normalized_text, alias, position, end):
                    candidates.append(
                        CandidateMention(
                            entity_id=entity.entity_id,
                            alias=alias,
                            start=position,
                            end=end,
                            cover=_count_letters_and_digits(
                                normalized_text[position:end]
                            ),
                        )
                    )
                position = normalized_text.find(alias, position + 1)
    return candidates
