"""Mention finding, optimal non-overlapping selection, and scoring."""

from __future__ import annotations

import unicodedata
from bisect import bisect_right
from dataclasses import dataclass

from entity_density.dictionary import EntityDictionary
from entity_density.normalize import normalize

_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


@dataclass(frozen=True)
class Mention:
    """One selected mention located in the normalized text."""

    entity_id: str
    alias: str
    start: int
    end: int


@dataclass(frozen=True)
class AnalysisResult:
    """Density score (0-100) plus the selected mentions."""

    score: int
    mentions: tuple[Mention, ...]
    normalized_text: str


def _is_word_char(ch: str) -> bool:
    return ch in _WORD_CHARS


def _is_letter_or_number(ch: str) -> bool:
    return unicodedata.category(ch)[0] in ("L", "N")


def _find_candidates(
    text: str, aliases: dict[str, str]
) -> list[tuple[int, int, str, str, int]]:
    candidates = []
    text_len = len(text)
    for alias, entity_id in aliases.items():
        head_bounded = _is_word_char(alias[0])
        tail_bounded = _is_word_char(alias[-1])
        start = text.find(alias)
        while start != -1:
            end = start + len(alias)
            left_ok = not (
                head_bounded and start > 0 and _is_word_char(text[start - 1])
            )
            right_ok = not (
                tail_bounded and end < text_len and _is_word_char(text[end])
            )
            if left_ok and right_ok:
                weight = sum(
                    1 for ch in text[start:end] if _is_letter_or_number(ch)
                )
                candidates.append((start, end, entity_id, alias, weight))
            start = text.find(alias, start + 1)
    return candidates


def _select_optimal(
    candidates: list[tuple[int, int, str, str, int]],
) -> list[tuple[int, int, str, str, int]]:
    """Weighted interval scheduling: max covered weight, then min count."""
    intervals = sorted(candidates, key=lambda c: (c[1], c[0]))
    ends = [c[1] for c in intervals]
    n = len(intervals)
    best: list[tuple[int, int]] = [(0, 0)]
    for i in range(n):
        prev = bisect_right(ends, intervals[i][0], 0, i)
        take_w = best[prev][0] + intervals[i][4]
        take_c = best[prev][1] + 1
        skip_w, skip_c = best[i]
        if (take_w, -take_c) > (skip_w, -skip_c):
            best.append((take_w, take_c))
        else:
            best.append((skip_w, skip_c))
    chosen = []
    i = n
    while i > 0:
        prev = bisect_right(ends, intervals[i - 1][0], 0, i - 1)
        take_w = best[prev][0] + intervals[i - 1][4]
        take_c = best[prev][1] + 1
        if (take_w, -take_c) > (best[i - 1][0], -best[i - 1][1]):
            chosen.append(intervals[i - 1])
            i = prev
        else:
            i -= 1
    chosen.reverse()
    return chosen


def analyze(text: str, dictionary: EntityDictionary) -> AnalysisResult:
    """Analyze plain text against a prepared dictionary."""
    normalized = normalize(text)
    candidates = _find_candidates(normalized, dictionary.aliases)
    chosen = _select_optimal(candidates)
    mentions = tuple(
        Mention(entity_id=c[2], alias=c[3], start=c[0], end=c[1])
        for c in chosen
    )
    total = sum(1 for ch in normalized if _is_letter_or_number(ch))
    covered = sum(c[4] for c in chosen)
    score = (100 * covered) // total if total else 0
    return AnalysisResult(
        score=score, mentions=mentions, normalized_text=normalized
    )
