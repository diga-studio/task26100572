import itertools
import random
import unittest
import unicodedata

from entity_density import EntityDictionary, analyze
from entity_density.analyzer import _find_candidates
from entity_density.normalize import normalize


def ln_count(text):
    return sum(1 for ch in text if unicodedata.category(ch)[0] in ("L", "N"))


def make_dict(entities):
    d = EntityDictionary()
    for entity_id, aliases in entities:
        d.add_entity(entity_id, aliases)
    return d


class NormalizeTest(unittest.TestCase):
    def test_fullwidth_case_and_whitespace(self):
        self.assertEqual(normalize("ＡＢＣ　ＸＹＺ"), "abc xyz")
        self.assertEqual(normalize("A\u00a0\u2003B\t\nC"), "a b c")

    def test_casefold(self):
        self.assertEqual(normalize("Straße"), "strasse")


class DictionaryTest(unittest.TestCase):
    def test_alias_lookup_uses_normalized_form(self):
        d = make_dict([("e1", ["ＡＩ", "甲乙"])])
        self.assertEqual(dict(d.aliases), {"ai": "e1", "甲乙": "e1"})

    def test_cross_entity_duplicate_alias_rejected(self):
        d = make_dict([("e1", ["AI"])])
        with self.assertRaises(ValueError):
            d.add_entity("e2", ["ａｉ"])

    def test_invalid_input_rejected(self):
        d = EntityDictionary()
        with self.assertRaises(ValueError):
            d.add_entity("", ["x"])
        with self.assertRaises(ValueError):
            d.add_entity("e1", [])
        with self.assertRaises(ValueError):
            d.add_entity("e1", ["  "])
        with self.assertRaises(ValueError):
            d.add_entity("e1", [""])
        d.add_entity("e1", ["x"])
        with self.assertRaises(ValueError):
            d.add_entity("e1", ["y"])


class BoundaryTest(unittest.TestCase):
    def test_english_alias_not_matched_inside_longer_word(self):
        d = make_dict([("e1", ["AI"])])
        self.assertEqual(analyze("said nothing", d).mentions, ())
        self.assertEqual(analyze("again", d).mentions, ())
        self.assertEqual(analyze("air", d).mentions, ())
        r = analyze("AI", d)
        self.assertEqual(len(r.mentions), 1)
        self.assertEqual(r.score, 100)

    def test_underscore_and_digit_are_word_chars(self):
        d = make_dict([("e1", ["AI"])])
        self.assertEqual(analyze("x_ai", d).mentions, ())
        self.assertEqual(analyze("ai9", d).mentions, ())
        self.assertEqual(analyze("9ai", d).mentions, ())

    def test_boundary_allows_punctuation_and_edges(self):
        d = make_dict([("e1", ["AI"])])
        for text in ("AI.", "(AI)", " AI ", "AI"):
            self.assertEqual(len(analyze(text, d).mentions), 1, text)

    def test_cjk_needs_no_spaces(self):
        d = make_dict([("e1", ["甲乙"])])
        r = analyze("丙甲乙丁", d)
        self.assertEqual(len(r.mentions), 1)
        self.assertEqual(r.mentions[0].start, 1)
        self.assertEqual(r.mentions[0].end, 3)

    def test_alias_with_non_word_tail_matches_before_word_char(self):
        d = make_dict([("e1", ["甲."])])
        self.assertEqual(len(analyze("甲.b", d).mentions), 1)


class ScoringTest(unittest.TestCase):
    def test_overlapping_aliases_pick_optimal_set(self):
        d = make_dict([
            ("e1", ["甲乙丙丁"]),
            ("e2", ["甲乙"]),
            ("e3", ["丙丁戊己"]),
        ])
        r = analyze("甲乙丙丁戊己", d)
        self.assertEqual(r.score, 100)
        self.assertEqual(
            {(m.entity_id, m.start, m.end) for m in r.mentions},
            {("e2", 0, 2), ("e3", 2, 6)},
        )

    def test_equivalent_writings_same_score(self):
        d = make_dict([("e1", ["ＡＩ　甲"]), ("e2", ["乙"])])
        base = analyze("AI 甲乙", d)
        for text in ("ａｉ　　甲乙", "AI\t甲乙", "ＡＩ 甲乙"):
            self.assertEqual(analyze(text, d).score, base.score, text)

    def test_score_is_floored_percentage(self):
        d = make_dict([("e1", ["甲"])])
        r = analyze("甲乙丙", d)
        self.assertEqual(r.score, 33)

    def test_zero_denominator_gives_zero(self):
        d = make_dict([("e1", ["甲"])])
        self.assertEqual(analyze(" ！？ ", d).score, 0)
        self.assertEqual(analyze("", d).score, 0)

    def test_repeated_mentions_count_separately(self):
        d = make_dict([("e1", ["甲"])])
        r = analyze("甲！甲", d)
        self.assertEqual(len(r.mentions), 2)
        self.assertEqual(r.score, 100)

    def test_same_span_not_double_counted(self):
        d = make_dict([("e1", ["ab", "AB"])])
        r = analyze("ab", d)
        self.assertEqual(len(r.mentions), 1)
        self.assertEqual(r.score, 100)

    def test_mentions_locate_normalized_text(self):
        d = make_dict([("e1", ["ＡＩ"]), ("e2", ["甲乙"])])
        r = analyze("说ＡＩ　甲乙！", d)
        for m in r.mentions:
            self.assertEqual(r.normalized_text[m.start:m.end], m.alias)

    def test_punctuation_counts_in_span_but_not_coverage(self):
        d = make_dict([("e1", ["a b"])])
        r = analyze("a b", d)
        self.assertEqual(r.score, 100)
        self.assertEqual((r.mentions[0].start, r.mentions[0].end), (0, 3))


class OptimalSelectionTest(unittest.TestCase):
    def test_matches_brute_force_on_random_short_texts(self):
        rng = random.Random(20261005)
        alias_pool = ["ab", "abc", "bc", "cd", "甲乙", "乙丙", "a"]
        for _ in range(200):
            entities = []
            picked = rng.sample(alias_pool, 3)
            for i, alias in enumerate(picked):
                entities.append((f"e{i}", [alias]))
            d = make_dict(entities)
            text = "".join(
                rng.choice("abcd甲乙丙 ") for _ in range(rng.randint(0, 8))
            )
            normalized = normalize(text)
            result = analyze(text, d)
            spans = sorted((m.start, m.end) for m in result.mentions)
            for i in range(len(spans) - 1):
                self.assertLessEqual(spans[i][1], spans[i + 1][0])
            covered = sum(
                ln_count(normalized[m.start:m.end]) for m in result.mentions
            )
            total = ln_count(normalized)
            expected_score = (100 * covered) // total if total else 0
            self.assertEqual(result.score, expected_score)
            candidates = _find_candidates(normalized, d.aliases)
            best_weight, best_count = 0, 0
            for r in range(len(candidates) + 1):
                for combo in itertools.combinations(candidates, r):
                    sp = sorted((c[0], c[1]) for c in combo)
                    if any(sp[i][1] > sp[i + 1][0] for i in range(len(sp) - 1)):
                        continue
                    w = sum(c[4] for c in combo)
                    if (w, -len(combo)) > (best_weight, -best_count):
                        best_weight, best_count = w, len(combo)
            self.assertEqual(covered, best_weight, text)
            self.assertEqual(len(result.mentions), best_count, text)


if __name__ == "__main__":
    unittest.main()
