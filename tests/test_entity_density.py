"""Automated tests for the entity_density library."""

from __future__ import annotations

import itertools
import random
import unicodedata

import pytest

from entity_density import analyze_text, normalize_text, prepare_dictionary
from entity_density.matching import find_candidates
from entity_density.selection import select_optimal


def make_dictionary():
    return prepare_dictionary(
        [
            {"id": "fruit-apple", "aliases": ["苹果", "Apple", "ａｐｐｌｅ"]},
            {"id": "fruit-banana", "aliases": ["香蕉"]},
            {"id": "company", "aliases": ["Open　AI", "openai"]},
        ]
    )


def brute_force_best(candidates):
    """Independent optimum: max covered letters/digits, then fewest mentions."""
    best_key = (0, 0)
    for size in range(len(candidates) + 1):
        for combo in itertools.combinations(candidates, size):
            ordered = sorted(combo, key=lambda c: c.start)
            if any(
                earlier.end > later.start
                for earlier, later in zip(ordered, ordered[1:])
            ):
                continue
            key = (sum(c.cover for c in combo), -len(combo))
            best_key = max(best_key, key)
    return best_key


class TestNormalization:
    def test_fullwidth_case_and_whitespace_equivalence(self):
        assert normalize_text("ＡＰＰＬＥ") == normalize_text("apple")
        assert normalize_text("Open　AI") == normalize_text("open  ai")
        assert normalize_text("a\t\n\r　b") == "a b"

    def test_casefold(self):
        assert normalize_text("Straße") == "strasse"

    def test_punctuation_is_kept(self):
        assert normalize_text("a,b!") == "a,b!"

    def test_equivalent_writings_give_same_score(self):
        dictionary = make_dictionary()
        baseline = analyze_text(dictionary, "苹果和apple都是水果")
        for variant in (
            "苹果和ＡＰＰＬＥ都是水果",
            "苹果和  Apple  都是水果",
            "苹果和　ａｐｐｌｅ　都是水果",
        ):
            result = analyze_text(dictionary, variant)
            assert result.score == baseline.score
            assert result.covered_characters == baseline.covered_characters
            assert result.total_characters == baseline.total_characters


class TestDictionary:
    def test_cross_entity_duplicate_alias_rejected(self):
        with pytest.raises(ValueError):
            prepare_dictionary(
                [
                    {"id": "a", "aliases": ["ABC"]},
                    {"id": "b", "aliases": ["ａｂｃ"]},
                ]
            )

    def test_same_entity_duplicate_aliases_collapsed(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["X", "ｘ"]}])
        assert dictionary.entities[0].aliases == ("x",)

    @pytest.mark.parametrize(
        "entities",
        [
            [{"id": "a", "aliases": []}],
            [{"id": "a", "aliases": ["   "]}],
            [{"id": "", "aliases": ["x"]}],
            [{"id": "a", "aliases": ["x"]}, {"id": "a", "aliases": ["y"]}],
        ],
    )
    def test_invalid_definitions_rejected(self, entities):
        with pytest.raises(ValueError):
            prepare_dictionary(entities)

    def test_dictionary_is_reusable(self):
        dictionary = make_dictionary()
        first = analyze_text(dictionary, "苹果")
        second = analyze_text(dictionary, "苹果和香蕉")
        assert first.score == 100
        assert second.score == 80


class TestBoundaries:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("cat", 1),
            ("a cat.", 1),
            ("cat-cat", 2),
            ("cats", 0),
            ("scat", 0),
            ("cat_2", 0),
            ("mycat2", 0),
            ("_cat", 0),
            ("9cat", 0),
            ("cat9", 0),
            ("cat猫", 1),
        ],
    )
    def test_ascii_word_boundaries(self, text, expected):
        dictionary = prepare_dictionary([{"id": "e", "aliases": ["cat"]}])
        result = analyze_text(dictionary, text)
        assert len(result.mentions) == expected

    def test_chinese_needs_no_spaces(self):
        dictionary = prepare_dictionary([{"id": "e", "aliases": ["苹果"]}])
        result = analyze_text(dictionary, "吃苹果派")
        assert len(result.mentions) == 1
        assert result.mentions[0].start == 1

    def test_underscore_is_a_word_char(self):
        dictionary = prepare_dictionary([{"id": "e", "aliases": ["cat_2"]}])
        assert len(analyze_text(dictionary, "cat_2").mentions) == 1
        assert len(analyze_text(dictionary, "cat_22").mentions) == 0
        assert len(analyze_text(dictionary, "acat_2").mentions) == 0


class TestSelection:
    def test_spec_example_full_coverage(self):
        dictionary = prepare_dictionary(
            [
                {"id": "e1", "aliases": ["甲乙丙丁"]},
                {"id": "e2", "aliases": ["甲乙"]},
                {"id": "e3", "aliases": ["丙丁戊己"]},
            ]
        )
        result = analyze_text(dictionary, "甲乙丙丁戊己")
        assert result.score == 100
        assert [m.entity_id for m in result.mentions] == ["e2", "e3"]

    def test_fewer_mentions_preferred_on_tie(self):
        dictionary = prepare_dictionary(
            [
                {"id": "whole", "aliases": ["abcd"]},
                {"id": "left", "aliases": ["ab"]},
                {"id": "right", "aliases": ["cd"]},
            ]
        )
        result = analyze_text(dictionary, "abcd")
        assert [m.entity_id for m in result.mentions] == ["whole"]

    def test_adjacent_mentions_do_not_overlap(self):
        dictionary = prepare_dictionary(
            [
                {"id": "a", "aliases": ["甲乙"]},
                {"id": "b", "aliases": ["丙丁"]},
            ]
        )
        result = analyze_text(dictionary, "甲乙丙丁")
        assert len(result.mentions) == 2
        assert result.score == 100

    def test_same_span_cannot_count_twice(self):
        dictionary = prepare_dictionary(
            [
                {"id": "a", "aliases": ["xy"]},
                {"id": "b", "aliases": ["xy "]},
            ]
        )
        result = analyze_text(dictionary, "xy xy")
        assert result.covered_characters == 4
        assert result.score == 100

    def test_repeated_mentions_count_separately(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["猫"]}])
        result = analyze_text(dictionary, "猫猫猫")
        assert len(result.mentions) == 3
        assert result.covered_characters == 3

    def test_random_short_texts_match_brute_force(self):
        rng = random.Random(20261005)
        alias_pool = ["ab", "bc", "abc", "a b", "甲", "甲乙", "b甲"]
        for _ in range(200):
            chosen_aliases = rng.sample(alias_pool, k=rng.randint(1, 4))
            dictionary = prepare_dictionary(
                [
                    {"id": "e%d" % index, "aliases": [alias]}
                    for index, alias in enumerate(dict.fromkeys(chosen_aliases))
                ]
            )
            text = "".join(rng.choice("ab 甲乙") for _ in range(rng.randint(0, 9)))
            normalized = normalize_text(text)
            candidates = find_candidates(dictionary, normalized)
            selected = select_optimal(candidates, len(normalized))

            expected_cover, expected_neg_count = brute_force_best(candidates)
            assert sum(c.cover for c in selected) == expected_cover
            assert -len(selected) == expected_neg_count


class TestScoring:
    def test_score_is_floored_percentage(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["ab"]}])
        result = analyze_text(dictionary, "ab c")
        assert result.covered_characters == 2
        assert result.total_characters == 3
        assert result.score == 66

    def test_zero_denominator_scores_zero(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["！"]}])
        result = analyze_text(dictionary, "！！！")
        assert result.score == 0
        assert result.total_characters == 0

    def test_empty_text(self):
        dictionary = make_dictionary()
        result = analyze_text(dictionary, "")
        assert result.score == 0
        assert result.mentions == ()

    def test_spaces_and_punctuation_do_not_count(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["a! b"]}])
        result = analyze_text(dictionary, "a! b")
        assert result.score == 100
        assert result.covered_characters == 2

    def test_unicode_letters_and_digits_count(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["é２"]}])
        result = analyze_text(dictionary, "é２")
        assert result.score == 100
        assert result.total_characters == 2


class TestExplainability:
    def test_mentions_locate_into_normalized_text(self):
        dictionary = make_dictionary()
        result = analyze_text(dictionary, "我爱ＡＰＰＬＥ和香蕉")
        assert result.normalized_text == "我爱apple和香蕉"
        for mention in result.mentions:
            assert result.normalized_text[mention.start : mention.end] == mention.text
            assert mention.text == mention.alias
        assert {m.entity_id for m in result.mentions} == {"fruit-apple", "fruit-banana"}

    def test_mentions_are_ordered_and_non_overlapping(self):
        dictionary = make_dictionary()
        result = analyze_text(dictionary, "香蕉 苹果 苹果")
        starts = [m.start for m in result.mentions]
        assert starts == sorted(starts)
        for earlier, later in zip(result.mentions, result.mentions[1:]):
            assert earlier.end <= later.start

    def test_cover_counts_only_letters_and_digits(self):
        dictionary = prepare_dictionary([{"id": "a", "aliases": ["x-y"]}])
        result = analyze_text(dictionary, "x-y")
        mention = result.mentions[0]
        covered = sum(
            1
            for char in mention.text
            if unicodedata.category(char)[0] in ("L", "N")
        )
        assert result.covered_characters == covered == 2
