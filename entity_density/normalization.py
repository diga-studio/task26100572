"""Text normalization shared by dictionaries and document analysis."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize text: NFKC, casefold, collapse Unicode whitespace runs.

    The result is the single source of truth for matching, character
    counting, and reported positions.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.casefold()
    return _WHITESPACE_RUN.sub(" ", normalized)
