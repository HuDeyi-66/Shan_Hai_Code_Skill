"""V2.3 -- ShanHai seal-blocker regression tests.

These tests exist because the V2.3 post-implementation review reproduced four
evidence-correctness defects that the capability tests did not cover, and the
review's verdict was that the number of passing tests could not substitute for
closing them. Each class here pins one defect class to a falsifiable property,
using the same reproduction the review used:

1. :class:`ArtifactIntegrityGateTests` -- bytes are verified against the recorded
   digest *before* extraction. A mismatch yields no units and a fatal,
   attributable diagnostic; it never yields units whose provenance claims a
   digest that was not true of what was read.
2. :class:`NoSilentOmissionTests` -- there is no option that returns less than the
   document contains. No detected provision may be absent from the evidence.
3. :class:`ZeroUnitInvariantTests` -- no option combination produces zero units,
   and the run-level backstop fails closed if one ever does.
4. :class:`StructuralVocabularyTruthfulnessTests` -- every code in
   ``StructuralCode.ALL`` is reachable from a fixture, and ``missing_marker``,
   ``malformed_marker`` and ``numbering_gap`` are three distinct states rather
   than three names for one.
5. :class:`DuplicateHandleTests` -- repeated article numbers get distinct unit
   handles while citations still return ambiguity instead of selecting a winner.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import _bootstrap  # noqa: E402

from skills.shanhai.contracts import TextArtifact, text_digest_bytes  # noqa: E402
from skills.shanhai.contracts import TextUnitClass  # noqa: E402
from skills.shanhai import (  # noqa: E402
    DEFAULT_OPTIONS,
    FixtureTextBackend,
    ShanHaiLegalTextEvidence,
    StructuralCode,
    TextAmbiguous,
    TextCitation,
    TextCitationSelector,
    iter_provisions,
    loss_kinds_for,
    read_text_bytes,
    resolve_text_citation_across,
    unit_text_provisions,
)
from fixtures.shanhai import build_text_fixtures as fixtures  # noqa: E402

SOURCE_ID = "src-integrity"


def artifact_for(case: str) -> TextArtifact:
    return TextArtifact.from_file(fixtures.case_path(case), f"art-{case}")


def run_case(case: str, **options):
    skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
    return skill.run(
        artifact_for(case), source_id=SOURCE_ID, options=options or None
    )


def codes_of(result) -> list[str]:
    return list(result.diagnostics.stats["structural_codes"])


# --------------------------------------------------------------------------
# 1. artifact integrity
# --------------------------------------------------------------------------


class ArtifactIntegrityGateTests(unittest.TestCase):
    """The bytes must match the registered digest before anything is decoded."""

    def test_a_mismatched_digest_yields_no_units_and_a_fatal_diagnostic(self) -> None:
        path = fixtures.case_path("normal")
        raw = path.read_bytes()
        # A digest of *different* bytes: the file on disk is not what was
        # registered. The Skill must refuse rather than read it anyway.
        artifact = TextArtifact(
            artifact_id="art-wrong-digest",
            digest=text_digest_bytes(raw + b"padding"),
            media_type="text/plain",
            byte_length=len(raw),
            location=str(path),
        )
        self.assertFalse(artifact.verify_file(path), "the probe must be a mismatch")

        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id=SOURCE_ID
        )

        self.assertEqual(result.units, ())
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertFalse(result.is_complete_success)
        self.assertFalse(result.diagnostics.stats["integrity_verified"])
        self.assertEqual(result.diagnostics.stats["unit_count"], 0)
        self.assertEqual(
            [e.code for e in result.diagnostics.errors],
            ["artifact_integrity_mismatch"],
        )

    def test_the_integrity_failure_names_both_digests(self) -> None:
        """Attributable: a caller can see which digest was expected and observed."""
        path = fixtures.case_path("normal")
        raw = path.read_bytes()
        recorded = text_digest_bytes(raw + b"padding")
        observed = text_digest_bytes(raw)
        artifact = TextArtifact(
            artifact_id="art-wrong-digest",
            digest=recorded,
            media_type="text/plain",
            byte_length=len(raw),
            location=str(path),
        )
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id=SOURCE_ID
        )
        message = result.diagnostics.errors[0].message
        self.assertIn(recorded, message)
        self.assertIn(observed, message)

    def test_no_unit_provenance_is_written_for_unverified_bytes(self) -> None:
        """The defect: units were emitted carrying a digest never true of the read."""
        path = fixtures.case_path("normal")
        raw = path.read_bytes()
        artifact = TextArtifact(
            artifact_id="art-wrong-digest",
            digest=text_digest_bytes(raw + b"padding"),
            media_type="text/plain",
            byte_length=len(raw),
            location=str(path),
        )
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id=SOURCE_ID
        )
        self.assertEqual(
            [u for u in result.units if u.provenance_is_recorded],
            [],
            "an unverified artifact must not produce provenance-bearing units",
        )

    def test_an_unreadable_artifact_fails_closed(self) -> None:
        artifact = TextArtifact(
            artifact_id="art-missing-file",
            digest="0" * 64,
            media_type="text/plain",
            byte_length=0,
            location=str(fixtures.GENERATED_DIR / "not_on_disk.txt"),
        )
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id=SOURCE_ID
        )
        self.assertEqual(result.units, ())
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertFalse(result.is_complete_success)

    def test_verified_bytes_are_recorded_and_flagged(self) -> None:
        artifact = artifact_for("normal")
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id=SOURCE_ID
        )
        self.assertTrue(result.diagnostics.stats["integrity_verified"])
        self.assertTrue(result.units)
        for unit in result.units:
            with self.subTest(unit=unit.unit_id):
                self.assertEqual(unit.provenance, artifact.content_digest)


# --------------------------------------------------------------------------
# 2. no silent omission
# --------------------------------------------------------------------------


class NoSilentOmissionTests(unittest.TestCase):
    """Nothing may shorten the evidence without the caller being able to see it."""

    def test_no_truncation_switch_exists(self) -> None:
        self.assertNotIn(
            "max_provisions",
            DEFAULT_OPTIONS,
            "a caller-selectable truncation switch is silent content omission; "
            "the option was removed rather than repaired",
        )

    def test_passing_a_truncation_option_cannot_shorten_the_output(self) -> None:
        """An unknown option must not be able to drop provisions.

        The old ``max_provisions`` slice left the loss at document level and still
        reported ``is_complete_success``. Whatever a caller passes now, the units
        must describe the whole document.
        """
        reference = run_case("normal")
        for options in (
            {"max_provisions": 0},
            {"max_provisions": 1},
            {"max_provisions": 99},
        ):
            with self.subTest(options=options):
                result = run_case("normal", **options)
                self.assertEqual(
                    result.diagnostics.stats["provision_numbers"], [1, 2, 3, 4, 5]
                )
                self.assertEqual(len(result.units), len(reference.units))
                self.assertTrue(result.is_complete_success)

    def test_no_detected_provision_is_dropped_from_the_evidence(self) -> None:
        """The reader's provisions and the units' provisions must agree exactly.

        Checked against the reader rather than against the Skill's own unit
        builder, so a future slice, filter or early return shows up as a
        disagreement instead of silently redefining the expectation.
        """
        for case in fixtures.CASES:
            with self.subTest(case=case):
                document = read_text_bytes(fixtures.fixture_bytes(case))
                expected = sorted(
                    (p.number, p.span.char_start) for p in document.provisions
                )
                result = run_case(case)
                actual = sorted(
                    (int(p["number"]), int(p["span"]["char_start"]))
                    for _, p in iter_provisions(result.units)
                )
                self.assertEqual(actual, expected)

    def test_every_structural_line_appears_in_some_unit(self) -> None:
        """No line that looks like a marker may be absent from the evidence.

        The check is deliberately independent of the Skill's own regexes: it
        selects lines that begin with ``第`` and asserts each lies inside some
        unit's recorded text. A resolved article, a chapter heading and a
        provisional fragment all count; a line that appears nowhere does not.
        """
        for case in fixtures.CASES:
            with self.subTest(case=case):
                text = read_text_bytes(fixtures.fixture_bytes(case)).text
                structural = [
                    line
                    for line in text.split("\n")
                    if line.strip().startswith("第")
                ]
                result = run_case(case)
                covered = "\n".join(
                    unit.content_raw or "" for unit in result.units
                )
                for line in structural:
                    self.assertIn(
                        line.strip(),
                        covered,
                        f"{case}: {line.strip()!r} appears in no evidence unit",
                    )

    def test_the_unreadable_markers_own_text_is_still_reachable(self) -> None:
        """A marker this reader cannot read must not take its article's text away.

        ``第廿条`` is a real article whose number the reader cannot resolve. If the
        line were skipped, the article would vanish from the evidence with only a
        structural code to show for it -- content omission disguised as a
        diagnostic.
        """
        document = read_text_bytes(fixtures.fixture_bytes("missing_marker"))
        unreadable = [p for p in document.provisions if p.number < 0]
        self.assertEqual(len(unreadable), 1, "the fixture must carry one such marker")

        result = run_case("missing_marker")
        carrying = [
            unit
            for unit in result.units
            if any(int(p["number"]) < 0 for p in unit_text_provisions(unit))
        ]
        self.assertEqual(len(carrying), 1)
        unit = carrying[0]
        self.assertIn(unreadable[0].marker, unit.content_raw)
        self.assertEqual(
            unit.content_raw,
            unreadable[0].span.extract(document.text),
            "the provisional unit must hold exactly the text the reader recorded",
        )


# --------------------------------------------------------------------------
# 3. zero-unit invariant
# --------------------------------------------------------------------------


class _NeverBuildsUnits(ShanHaiLegalTextEvidence):
    """A Skill whose unit builder is forced to return nothing.

    The reader always yields at least one unit, so the run-level backstop is not
    reachable through any option combination. Forcing it here is the only way to
    prove the backstop fails closed rather than returning an empty success.
    """

    def _build_units(self, **kwargs):  # type: ignore[override]
        return ()


class ZeroUnitInvariantTests(unittest.TestCase):
    """No run may return zero units and claim to have succeeded."""

    OPTION_SETS: tuple[dict, ...] = (
        {},
        {"emit_chapter_units": True},
        {"emit_chapter_units": False},
        {"max_provisions": 0},
        {"max_provisions": 1},
        {"emit_chapter_units": False, "max_provisions": 0},
        {"backends": [FixtureTextBackend()]},
    )

    def test_no_option_combination_produces_zero_units(self) -> None:
        for case in fixtures.CASES:
            for options in self.OPTION_SETS:
                with self.subTest(case=case, options=options):
                    result = run_case(case, **options)
                    self.assertTrue(
                        result.units,
                        "a run with no units cannot be distinguished from a "
                        "complete extraction failure",
                    )

    def test_the_run_level_backstop_fails_closed(self) -> None:
        skill = _NeverBuildsUnits(FixtureTextBackend())
        result = skill.run(artifact_for("normal"), source_id=SOURCE_ID)
        self.assertEqual(result.units, ())
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertFalse(result.is_complete_success)
        self.assertEqual(
            [e.code for e in result.diagnostics.errors], ["zero_units_emitted"]
        )

    def test_an_empty_result_is_never_a_complete_success(self) -> None:
        """The property the invariant exists for, stated directly."""
        for case in fixtures.CASES:
            for options in self.OPTION_SETS:
                with self.subTest(case=case, options=options):
                    result = run_case(case, **options)
                    if not result.units:
                        self.assertFalse(result.is_complete_success)


# --------------------------------------------------------------------------
# 4. structural vocabulary truthfulness
# --------------------------------------------------------------------------


class StructuralVocabularyTruthfulnessTests(unittest.TestCase):
    """Declared states must be reachable, and must not be aliases of each other."""

    def test_every_declared_structural_code_is_reachable(self) -> None:
        """No code may be declared that no fixture can produce.

        ``missing_marker`` was declared but unreachable before this patch: every
        document that should have produced it reported ``numbering_gap`` instead.
        """
        reachable: set[str] = set()
        for case in fixtures.CASES:
            reachable.update(codes_of(run_case(case)))
        self.assertEqual(
            set(StructuralCode.ALL) - reachable,
            set(),
            "declared but unreachable structural code(s)",
        )

    def test_missing_marker_malformed_marker_and_gap_are_three_states(self) -> None:
        missing = run_case("missing_marker")
        malformed = run_case("malformed_marker")
        gap = run_case("numbering_gap_no_marker")

        self.assertEqual(codes_of(missing), [StructuralCode.MISSING_MARKER])
        self.assertEqual(codes_of(malformed), [StructuralCode.MALFORMED_MARKER])
        self.assertEqual(codes_of(gap), [StructuralCode.NUMBERING_GAP])

        # ...and the three conditions involve different numbering facts.
        self.assertEqual(missing.diagnostics.stats["provision_numbers"], [1, -1, 21])
        self.assertEqual(malformed.diagnostics.stats["provision_numbers"], [1, -1, 3])
        self.assertEqual(gap.diagnostics.stats["provision_numbers"], [1, 3])

        for result in (missing, malformed, gap):
            self.assertFalse(result.is_complete_success)

    def test_the_unreadable_marker_is_not_reported_as_a_gap(self) -> None:
        """The specific conflation: 第廿条 is present but unreadable, not absent."""
        result = run_case("missing_marker")
        self.assertNotIn(StructuralCode.NUMBERING_GAP, codes_of(result))
        self.assertNotIn(StructuralCode.MALFORMED_MARKER, codes_of(result))

    def test_the_unit_loss_kind_matches_the_recorded_code(self) -> None:
        """Unit-level loss must name the same condition the document reports."""
        result = run_case("missing_marker")
        unreadable = [
            unit
            for unit in result.units
            if any(int(p["number"]) < 0 for p in unit_text_provisions(unit))
        ]
        self.assertEqual(len(unreadable), 1)
        unit = unreadable[0]
        expected = loss_kinds_for([StructuralCode.MISSING_MARKER])
        self.assertEqual(tuple(unit.loss), tuple(expected))
        self.assertIn(StructuralCode.MISSING_MARKER, unit.self_warnings[0])

    def test_a_malformed_marker_is_not_a_citation_target(self) -> None:
        """Distinct from a gap, and still not silently citable."""
        result = run_case("missing_marker")
        outcome = resolve_text_citation_across(
            result.units, TextCitationSelector(article_number=-1)
        )
        self.assertNotIsInstance(outcome, TextCitation)


# --------------------------------------------------------------------------
# 5. duplicate handles
# --------------------------------------------------------------------------


class DuplicateHandleTests(unittest.TestCase):
    """A repeated marker yields two units, two handles, and an ambiguous citation."""

    def test_unit_ids_are_unique_for_every_fixture(self) -> None:
        for case in fixtures.CASES:
            with self.subTest(case=case):
                result = run_case(case)
                ids = [u.unit_id for u in result.units]
                self.assertEqual(
                    len(ids),
                    len(set(ids)),
                    f"{case} produced duplicate unit handles: {sorted(ids)}",
                )

    def test_a_duplicated_marker_produces_two_distinct_handles(self) -> None:
        result = run_case("duplicate_marker")
        articles = [
            unit
            for unit in result.units
            if any(int(p["number"]) == 2 for p in unit_text_provisions(unit))
        ]
        self.assertEqual(len(articles), 2)
        ids = [u.unit_id for u in articles]
        self.assertEqual(len(set(ids)), 2, f"handles collided: {ids}")
        for unit in articles:
            self.assertTrue(unit.address.value.endswith(":2"))

    def test_the_distinct_handles_locate_different_text(self) -> None:
        result = run_case("duplicate_marker")
        articles = [
            unit
            for unit in result.units
            if any(int(p["number"]) == 2 for p in unit_text_provisions(unit))
        ]
        spans = [p["span"]["char_start"] for u in articles for p in unit_text_provisions(u)]
        self.assertEqual(len(set(spans)), 2)

    def test_a_duplicated_marker_is_ambiguous_not_auto_selected(self) -> None:
        result = run_case("duplicate_marker")
        outcome = resolve_text_citation_across(
            result.units, TextCitationSelector(article_number=2)
        )
        self.assertIsInstance(outcome, TextAmbiguous)
        self.assertEqual(len(outcome.candidates), 2)
        self.assertEqual(
            len({c.unit_id for c in outcome.candidates}),
            2,
            "the ambiguity must name two different units, not one twice",
        )

    def test_container_units_are_unique_too(self) -> None:
        """The same defect class applies to chapter containers."""
        result = run_case("normal")
        container_ids = [
            u.unit_id for u in result.units if u.unit_class == TextUnitClass.CONTAINER
        ]
        self.assertEqual(len(container_ids), len(set(container_ids)))

    def test_handles_are_stable_across_runs(self) -> None:
        first = [u.unit_id for u in run_case("duplicate_marker").units]
        second = [u.unit_id for u in run_case("duplicate_marker").units]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
