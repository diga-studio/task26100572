"""Text normalization shared by dictionaries and analysis."""

import re
import unicodedata

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize(text: str) -> str:
    """NFKC -> casefold -> collapse Unicode whitespace runs to one space."""
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    return _WHITESPACE_RUN.sub(" ", text)
