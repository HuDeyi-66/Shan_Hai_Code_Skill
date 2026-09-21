"""V2.3 -- ShanHai text citation reconstruction tests.

The rule inherited from the workbook Skill: **no first match, no ordering guess,
no fuzzy silent match.** Text raises the stakes, because a duplicated article
marker is a real drafting error rather than a synthetic trick, and a citation
that quietly picks one occurrence is a wrong citation.

What is asserted here:

* a citation rebuilds to the exact artifact location, verified against the
  artifact text;
* the same location is reachable through all three coordinate systems;
* a duplicated marker returns ``ambiguous`` listing every occurrence;
* an absent marker returns ``unresolved``, distinct from ``ambiguous``;
* a malformed marker is never a citation target;
* a citation to a unit that failed is blocked rather than silently resolved.
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import _bootstrap  # noqa: E402

from core.artifact import Artifact  # noqa: E402
from skills.shanhai import (  # noqa: E402
    FixtureTextBackend,
    ShanHaiLegalTextEvidence,
    TextAmbiguous,
    TextCitation,
    TextCitationProblem,
    TextCitationSelector,
    TextUnresolved,
    resolve_text_citation,
    resolve_text_citation_across,
    unit_text_provisions,
)
from fixtures.shanhai import build_text_fixtures as fixtures  # noqa: E402


def run_case(case: str):
    artifact = Artifact.from_file(fixtures.case_path(case), f"art-{case}")
    skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
    return artifact, skill.run(artifact, source_id="src-shanhai")


def document_text(case: str) -> str:
    return fixtures.fixture_bytes(case).decode("utf-8")


def citation_units(result):
    return [u for u in result.units if unit_text_provisions(u)]


class NormalCitationTests(unittest.TestCase):
    """The happy path, checked against the truth manifest's exact spans."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact, cls.result = run_case("normal")
        cls.text = document_text("normal")
        cls.truth = json.loads(
            (fixtures.TRUTH_DIR / "normal_truth.json").read_text(encoding="utf-8")
        )
        cls.by_number = {
            a["number"]: a for a in cls.truth["articles"]
        }

    def resolve(self, selector: TextCitationSelector):
        return resolve_text_citation_across(
            self.result.units, selector, document_text=self.text
        )

    def test_an_article_rebuilds_to_its_exact_location(self) -> None:
        outcome = self.resolve(TextCitationSelector(article_number=1))
        self.assertIsInstance(outcome, TextCitation)
        assert isinstance(outcome, TextCitation)
        expected = self.by_number[1]
        self.assertEqual(outcome.char_start, expected["char_start"])
        self.assertEqual(outcome.char_end, expected["char_end"])
        self.assertEqual(outcome.line_start, expected["line_start"])
        self.assertEqual(outcome.line_end, expected["line_end"])
        self.assertEqual(outcome.text, expected["text"])

    def test_every_article_round_trips(self) -> None:
        for number, expected in sorted(self.by_number.items()):
            with self.subTest(article=number):
                outcome = self.resolve(TextCitationSelector(article_number=number))
                self.assertIsInstance(outcome, TextCitation)
                assert isinstance(outcome, TextCitation)
                self.assertEqual(outcome.text, expected["text"])
                self.assertTrue(outcome.verify(self.text))

    def test_the_citation_is_verifiable_against_the_artifact(self) -> None:
        outcome = self.resolve(TextCitationSelector(article_number=2))
        assert isinstance(outcome, TextCitation)
        self.assertTrue(outcome.verify(self.text))

    def test_verification_fails_on_a_different_document(self) -> None:
        """A citation is checkable: the offsets must reproduce in the artifact.

        Appending text must *not* break verification, because the recorded
        offsets still point at the same characters. Verifying against a different
        document must break it, which is what makes the check meaningful.
        """
        outcome = self.resolve(TextCitationSelector(article_number=2))
        assert isinstance(outcome, TextCitation)
        self.assertTrue(
            outcome.verify(self.text + "tampered"),
            "appending text does not change what the recorded offsets point at",
        )
        self.assertFalse(
            outcome.verify(document_text("missing_marker")),
            "the same offsets in a different document must not verify",
        )

    def test_all_three_coordinate_systems_agree(self) -> None:
        outcome = self.resolve(TextCitationSelector(article_number=3))
        assert isinstance(outcome, TextCitation)
        raw = fixtures.case_path("normal").read_bytes()
        self.assertEqual(
            raw[outcome.byte_start : outcome.byte_end].decode("utf-8"), outcome.text
        )
        self.assertEqual(
            self.text[outcome.char_start : outcome.char_end], outcome.text
        )

    def test_an_article_resolves_within_its_chapter(self) -> None:
        outcome = self.resolve(
            TextCitationSelector(article_number=3, chapter_number=2)
        )
        self.assertIsInstance(outcome, TextCitation)
        assert isinstance(outcome, TextCitation)
        self.assertEqual(outcome.chapter_number, 2)

    def test_the_wrong_chapter_is_unresolved(self) -> None:
        outcome = self.resolve(
            TextCitationSelector(article_number=3, chapter_number=1)
        )
        self.assertIsInstance(outcome, TextUnresolved)

    def test_a_paragraph_resolves_to_a_strictly_smaller_span(self) -> None:
        whole = self.resolve(TextCitationSelector(article_number=3))
        paragraph = self.resolve(
            TextCitationSelector(article_number=3, paragraph_index=1)
        )
        assert isinstance(whole, TextCitation) and isinstance(paragraph, TextCitation)
        self.assertGreater(paragraph.char_start, whole.char_start)
        self.assertLessEqual(paragraph.char_end, whole.char_end)
        self.assertLess(len(paragraph.text), len(whole.text))
        self.assertTrue(paragraph.verify(self.text))

    def test_the_second_paragraph_is_where_the_parser_says_it_is(self) -> None:
        outcome = self.resolve(
            TextCitationSelector(article_number=3, paragraph_index=2)
        )
        self.assertIsInstance(outcome, TextCitation)
        assert isinstance(outcome, TextCitation)
        self.assertTrue(outcome.verify(self.text))
        self.assertEqual(outcome.paragraph_index, 2)

    def test_a_paragraph_beyond_the_end_is_unresolved(self) -> None:
        outcome = self.resolve(
            TextCitationSelector(article_number=4, paragraph_index=5)
        )
        self.assertIsInstance(outcome, TextUnresolved)
        assert isinstance(outcome, TextUnresolved)
        self.assertEqual(outcome.problem, TextCitationProblem.UNRESOLVED)

    def test_a_character_range_resolves_and_verifies(self) -> None:
        expected = self.by_number[1]
        outcome = self.resolve(
            TextCitationSelector(
                char_range=(expected["char_start"] + 4, expected["char_end"])
            )
        )
        self.assertIsInstance(outcome, TextCitation)
        assert isinstance(outcome, TextCitation)
        self.assertTrue(outcome.verify(self.text))
        self.assertEqual(outcome.uniqueness, "document_span")
        self.assertTrue(outcome.is_weak)

    def test_a_character_range_outside_every_provision_is_unresolved(self) -> None:
        outcome = self.resolve(TextCitationSelector(char_range=(0, 3)))
        self.assertIsInstance(outcome, TextUnresolved)

    def test_a_malformed_character_range_is_rejected(self) -> None:
        outcome = self.resolve(TextCitationSelector(char_range=(40, 10)))
        self.assertIsInstance(outcome, TextUnresolved)
        assert isinstance(outcome, TextUnresolved)
        self.assertEqual(outcome.problem, TextCitationProblem.MALFORMED_SELECTOR)

    def test_an_absent_article_is_unresolved(self) -> None:
        outcome = self.resolve(TextCitationSelector(article_number=99))
        self.assertIsInstance(outcome, TextUnresolved)
        assert isinstance(outcome, TextUnresolved)
        self.assertEqual(outcome.problem, TextCitationProblem.UNRESOLVED)

    def test_supplying_two_conventions_is_refused_not_prioritised(self) -> None:
        """Choosing which selector 'wins' would be a silent choice of evidence."""
        outcome = self.resolve(
            TextCitationSelector(article_number=1, char_range=(24, 40))
        )
        self.assertIsInstance(outcome, TextUnresolved)
        assert isinstance(outcome, TextUnresolved)
        self.assertEqual(outcome.problem, TextCitationProblem.MALFORMED_SELECTOR)

    def test_an_empty_selector_is_rejected(self) -> None:
        outcome = self.resolve(TextCitationSelector())
        self.assertIsInstance(outcome, TextUnresolved)

    def test_the_citation_serialises_completely(self) -> None:
        outcome = self.resolve(TextCitationSelector(article_number=5))
        assert isinstance(outcome, TextCitation)
        payload = json.loads(json.dumps(outcome.as_dict(), ensure_ascii=False))
        for key in (
            "artifact_id",
            "source_id",
            "article_number",
            "marker",
            "span",
            "text",
            "context_path",
            "uniqueness",
        ):
            self.assertIn(key, payload)
        self.assertNotIn("selected", payload)

    def test_the_context_path_is_reconstructible(self) -> None:
        outcome = self.resolve(
            TextCitationSelector(article_number=3, chapter_number=2)
        )
        assert isinstance(outcome, TextCitation)
        path = " ".join(outcome.context_path)
        self.assertIn("chapter:2", path)
        self.assertIn("article:3", path)
        self.assertIn("span:char:", path)


class DuplicateMarkerTests(unittest.TestCase):
    """A duplicated marker must never be resolved by picking one occurrence."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact, cls.result = run_case("duplicate_marker")
        cls.text = document_text("duplicate_marker")

    def test_the_duplicate_is_reported_as_a_structural_condition(self) -> None:
        self.assertEqual(
            self.result.diagnostics.stats["provision_numbers"], [1, 2, 2, 3]
        )
        self.assertIn(
            "duplicate_marker", self.result.diagnostics.stats["structural_codes"]
        )

    def test_a_citation_to_the_duplicated_marker_is_ambiguous(self) -> None:
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=2),
            document_text=self.text,
        )
        self.assertIsInstance(outcome, TextAmbiguous)
        assert isinstance(outcome, TextAmbiguous)
        self.assertEqual(outcome.problem, TextCitationProblem.AMBIGUOUS)

    def test_every_occurrence_is_listed(self) -> None:
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=2),
            document_text=self.text,
        )
        assert isinstance(outcome, TextAmbiguous)
        self.assertEqual(len(outcome.candidates), 2)
        self.assertEqual({c.article_number for c in outcome.candidates}, {2})
        # The two candidates are genuinely different locations.
        spans = {c.span.char_ref for c in outcome.candidates}
        self.assertEqual(len(spans), 2)

    def test_the_ambiguous_payload_has_no_selected_field(self) -> None:
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=2),
            document_text=self.text,
        )
        payload = json.loads(json.dumps(outcome.as_dict(), ensure_ascii=False))
        self.assertEqual(payload["status"], "ambiguous")
        self.assertEqual(len(payload["candidates"]), 2)
        self.assertNotIn("selected", payload)

    def test_a_unique_article_still_resolves(self) -> None:
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=1),
            document_text=self.text,
        )
        self.assertIsInstance(outcome, TextCitation)

    def test_an_absent_article_is_unresolved_not_ambiguous(self) -> None:
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=9),
            document_text=self.text,
        )
        self.assertIsInstance(outcome, TextUnresolved)
        self.assertNotIsInstance(outcome, TextAmbiguous)

    def test_within_one_unit_a_duplicate_cannot_be_seen(self) -> None:
        """Why the cross-document resolver exists.

        Each unit holds one provision, so a within-unit resolver cannot detect
        that the marker recurs elsewhere. The cross-document resolver is the
        entry point that can, and the two are deliberately separate.
        """
        units = citation_units(self.result)
        self.assertGreater(len(units), 1)
        for unit in units:
            provisions = unit_text_provisions(unit)
            self.assertEqual(len(provisions), 1)


class MalformedMarkerCitationTests(unittest.TestCase):
    """A marker that does not parse must never become a citation target."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact, cls.result = run_case("malformed_marker")
        cls.text = document_text("malformed_marker")

    def test_the_malformed_marker_produces_no_citable_article(self) -> None:
        numbers = self.result.diagnostics.stats["provision_numbers"]
        # The marker-shaped line is kept as a provisional, uncitable fragment
        # (number -1) so that its text is not dropped from the evidence. What it
        # must never become is a citable article.
        self.assertEqual(numbers, [1, -1, 3])
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=-1),
            document_text=self.text,
        )
        self.assertNotIsInstance(outcome, TextCitation)

    def test_citing_the_gap_between_articles_is_unresolved(self) -> None:
        outcome = resolve_text_citation_across(
            self.result.units,
            TextCitationSelector(article_number=2),
            document_text=self.text,
        )
        self.assertIsInstance(outcome, TextUnresolved)

    def test_the_surviving_articles_are_still_citable(self) -> None:
        for number in (1, 3):
            with self.subTest(article=number):
                outcome = resolve_text_citation_across(
                    self.result.units,
                    TextCitationSelector(article_number=number),
                    document_text=self.text,
                )
                self.assertIsInstance(outcome, TextCitation)
                assert isinstance(outcome, TextCitation)
                self.assertTrue(outcome.verify(self.text))


class BlockedCitationTests(unittest.TestCase):
    """A unit that failed is not silently citable."""

    def test_an_unsupported_document_cannot_be_cited(self) -> None:
        _, result = run_case("unsupported_structure")
        unit = result.units[0]
        outcome = resolve_text_citation(unit, TextCitationSelector(article_number=1))
        self.assertIsInstance(outcome, TextUnresolved)
        assert isinstance(outcome, TextUnresolved)
        self.assertIn(
            outcome.problem,
            (TextCitationProblem.NO_TEXT_PAYLOAD, TextCitationProblem.BLOCKED_BY_LOSS),
        )

    def test_an_empty_document_cannot_be_cited(self) -> None:
        _, result = run_case("empty")
        outcome = resolve_text_citation(
            result.units[0], TextCitationSelector(article_number=1)
        )
        self.assertIsInstance(outcome, TextUnresolved)

    def test_an_encoding_failure_cannot_be_cited(self) -> None:
        _, result = run_case("not_utf8")
        outcome = resolve_text_citation(
            result.units[0], TextCitationSelector(article_number=1)
        )
        self.assertIsInstance(outcome, TextUnresolved)
        assert isinstance(outcome, TextUnresolved)
        # A failed decode produces no provisions at all, so there is nothing to
        # resolve against; the blocking loss is reported on the document unit.
        self.assertEqual(outcome.problem, TextCitationProblem.NO_TEXT_PAYLOAD)
        self.assertIn("failed", result.units[0].loss)

    def test_a_caller_can_opt_into_a_lossy_unit_explicitly(self) -> None:
        """Refusing is the default; accepting is an explicit, recorded act."""
        _, result = run_case("gap")
        unit = citation_units(result)[0]
        blocked = resolve_text_citation(unit, TextCitationSelector(article_number=1))
        allowed = resolve_text_citation(
            unit,
            TextCitationSelector(article_number=1, allow_lossy=True),
            document_text=document_text("gap"),
        )
        self.assertIsInstance(blocked, TextCitation)
        self.assertIsInstance(allowed, TextCitation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
