"""Optimal non-overlapping mention selection."""

from __future__ import annotations

from .matching import CandidateMention


def select_optimal(candidates: list[CandidateMention], text_length: int) -> list[CandidateMention]:
    """Select a non-overlapping subset of mentions.

    Maximizes the total covered letter/number characters; ties are broken
    by minimizing the number of selected mentions. Adjacent (touching)
    mentions do not overlap.
    """
    starts: dict[int, list[CandidateMention]] = {}
    for candidate in candidates:
        if candidate.cover > 0:
            starts.setdefault(candidate.start, []).append(candidate)

    # best[position] = (covered, -mentions, chosen) for text[position:].
    sentinel = -10**18
    best: list[tuple[int, int, tuple[CandidateMention, ...]]] = [
        (sentinel, sentinel, ()) for _ in range(text_length + 1)
    ]
    best[text_length] = (0, 0, ())

    for position in range(text_length - 1, -1, -1):
        skip_cover, skip_neg_count, skip_chosen = best[position + 1]
        best_cover, best_neg_count, best_chosen = skip_cover, skip_neg_count, skip_chosen
        for candidate in starts.get(position, ()):
            rest_cover, rest_neg_count, rest_chosen = best[candidate.end]
            cover = candidate.cover + rest_cover
            neg_count = rest_neg_count - 1
            if (cover, neg_count) > (best_cover, best_neg_count):
                best_cover, best_neg_count = cover, neg_count
                best_chosen = (candidate,) + rest_chosen
        best[position] = (best_cover, best_neg_count, best_chosen)

    return list(best[0][2])
