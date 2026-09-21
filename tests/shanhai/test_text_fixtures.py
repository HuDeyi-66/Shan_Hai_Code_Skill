"""V2.3 -- ShanHai fixture reproducibility and text-reader tests.

Two things are pinned here:

1. the fixtures rebuild **byte-identically**, so a parsing difference can never
   be blamed on fixture drift;
2. the exact-offset machinery -- character, byte and line spans -- is correct
   against the fixture bytes, including for multi-byte CJK text where a naive
   byte/character confusion would show up immediately.
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
    TextSpan,
    read_text_bytes,
    read_text_document,
)
from skills.shanhai import textio  # noqa: E402
from fixtures.shanhai import build_text_fixtures as fixtures  # noqa: E402


class FixtureReproducibilityTests(unittest.TestCase):
    def test_every_case_rebuilds_byte_identically(self) -> None:
        for case in fixtures.CASES:
            with self.subTest(case=case):
                first = fixtures.fixture_bytes(case)
                second = fixtures.fixture_bytes(case)
                self.assertEqual(first, second)

    def test_written_fixtures_match_the_manifest(self) -> None:
        manifest = json.loads(
            (fixtures.GENERATED_DIR / "cases.json").read_text(encoding="utf-8")
        )
        for case, spec in manifest["cases"].items():
            with self.subTest(case=case):
                payload = fixtures.case_path(case).read_bytes()
                self.assertEqual(fixtures._sha256(payload), spec["sha256"])
                self.assertEqual(len(payload), spec["bytes"])

    def test_rebuild_matches_the_committed_fixture(self) -> None:
        for case in fixtures.CASES:
            with self.subTest(case=case):
                self.assertEqual(
                    fixtures.fixture_bytes(case),
                    fixtures.case_path(case).read_bytes(),
                    f"{case} drifted; regenerate the fixtures and truth manifest "
                    f"together",
                )

    def test_a_full_write_cycle_is_idempotent(self) -> None:
        before = {
            case: fixtures.case_path(case).read_bytes() for case in fixtures.CASES
        }
        truth_before = (
            fixtures.TRUTH_DIR / "normal_truth.json"
        ).read_text(encoding="utf-8")
        fixtures.write_fixtures()
        for case, payload in before.items():
            with self.subTest(case=case):
                self.assertEqual(fixtures.case_path(case).read_bytes(), payload)
        self.assertEqual(
            (fixtures.TRUTH_DIR / "normal_truth.json").read_text(encoding="utf-8"),
            truth_before,
        )

    def test_fixtures_are_utf8_lf_and_bom_free(self) -> None:
        for case in fixtures.CASES:
            if case == "not_utf8":
                continue
            with self.subTest(case=case):
                raw = fixtures.case_path(case).read_bytes()
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "BOM present")
                self.assertNotIn(b"\r\n", raw, "CRLF present")
                raw.decode("utf-8")  # must not raise

    def test_the_truth_manifest_is_pinned_to_the_fixture(self) -> None:
        truth = json.loads(
            (fixtures.TRUTH_DIR / "normal_truth.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            truth["fixture_sha256"],
            fixtures._sha256(fixtures.fixture_bytes("normal")),
        )

    def test_every_structural_condition_has_a_fixture(self) -> None:
        covered = {spec["condition"] for spec in fixtures.CASES.values()}
        for condition in (
            "empty_artifact",
            "unsupported_structure",
            "missing_marker",
            "malformed_marker",
            "numbering_gap",
            "duplicate_marker",
            "encoding_failure",
        ):
            with self.subTest(condition=condition):
                self.assertIn(condition, covered)

    def test_the_normal_fixture_has_chapters_articles_and_paragraphs(self) -> None:
        document = read_text_document(fixtures._text_of(fixtures.NORMAL_LINES))
        self.assertEqual(len(document.chapters), 2)
        self.assertEqual(len(document.provisions), 5)
        self.assertTrue(
            any(p.paragraphs > 1 for p in document.provisions),
            "the normal fixture must exercise multi-paragraph articles",
        )


class OffsetTests(unittest.TestCase):
    """The offset machinery, checked independently of the parser."""

    def test_line_offsets_cover_every_line(self) -> None:
        text = "a\nbb\n\nccc"
        starts, ends = textio.line_offsets(text)
        self.assertEqual(len(starts), len(ends))
        self.assertEqual(len(starts), 4)
        for index, (start, end) in enumerate(zip(starts, ends)):
            with self.subTest(line=index + 1):
                self.assertEqual(text[start:end], text.split("\n")[index])

    def test_an_empty_document_still_has_one_line(self) -> None:
        starts, ends = textio.line_offsets("")
        self.assertEqual(len(starts), 1)
        self.assertEqual(starts, [0])
        self.assertEqual(ends, [0])

    def test_span_extract_returns_exactly_the_recorded_text(self) -> None:
        text = "中华人民共和国海商法"
        span = TextSpan(
            char_start=2, char_end=5, byte_start=6, byte_end=15, line_start=1, line_end=1
        )
        self.assertEqual(span.extract(text), "人民共")
        self.assertEqual(len(span.extract(text).encode("utf-8")), span.byte_length)

    def test_a_reversed_span_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TextSpan(
                char_start=5, char_end=2, byte_start=0, byte_end=1, line_start=1, line_end=1
            )

    def test_multi_byte_text_gets_distinct_char_and_byte_offsets(self) -> None:
        document = read_text_document(fixtures._text_of(fixtures.NORMAL_LINES))
        for provision in document.provisions:
            span = provision.span
            with self.subTest(article=provision.number):
                self.assertGreater(
                    span.byte_length,
                    span.char_length,
                    "CJK text must have more bytes than characters",
                )
                self.assertEqual(
                    len(provision.text.encode("utf-8")), span.byte_length
                )

    def test_every_byte_span_slices_the_fixture_bytes_correctly(self) -> None:
        raw = fixtures.fixture_bytes("normal")
        document = read_text_bytes(raw)
        for provision in document.provisions:
            span = provision.span
            with self.subTest(article=provision.number):
                self.assertEqual(
                    raw[span.byte_start : span.byte_end].decode("utf-8"),
                    provision.text,
                )

    def test_newline_normalization_is_recorded_not_silent(self) -> None:
        document = read_text_document("第一条 内容。\r\n第二条 内容。\r\n")
        self.assertTrue(document.metadata.get("newline_normalized"))
        self.assertNotIn("\r", document.text)


class ReaderTests(unittest.TestCase):
    """The reader's own contract."""

    def test_an_empty_artifact_is_empty_not_success(self) -> None:
        document = read_text_bytes(b"")
        self.assertEqual([code for code, _ in document.structural_findings], ["empty_artifact"])
        self.assertEqual(document.provisions, ())
        self.assertTrue(document.loss)

    def test_whitespace_only_is_treated_as_empty(self) -> None:
        document = read_text_document("   \n\n\t\n")
        self.assertEqual(
            [code for code, _ in document.structural_findings], ["empty_artifact"]
        )

    def test_a_document_without_markers_is_unsupported(self) -> None:
        document = read_text_document("Just some prose.\n\nNo numbered markers here.\n")
        self.assertEqual(
            [code for code, _ in document.structural_findings],
            ["unsupported_structure"],
        )

    def test_an_invalid_utf8_artifact_is_not_lossily_decoded(self) -> None:
        raw = "测试".encode("utf-16-le") + b"\xff\xfe"
        document = read_text_bytes(raw)
        self.assertTrue(document.fatal)
        self.assertEqual(document.text, "")
        self.assertEqual(
            [code for code, _ in document.structural_findings], ["encoding_failure"]
        )

    def test_a_missing_file_is_reported_not_raised(self) -> None:
        document = FixtureTextBackend().load(str(fixtures.GENERATED_DIR / "nope.txt"))
        self.assertTrue(document.fatal)
        self.assertTrue(document.errors)

    def test_the_backend_is_read_only(self) -> None:
        path = fixtures.case_path("normal")
        before = path.read_bytes()
        FixtureTextBackend().load(str(path))
        self.assertEqual(path.read_bytes(), before)

    def test_arabic_and_cjk_numerals_both_parse(self) -> None:
        document = read_text_document("第1条 阿拉伯数字。\n\n第二条 中文数字。\n")
        self.assertEqual([p.number for p in document.provisions], [1, 2])

    def test_a_large_cjk_numeral_parses(self) -> None:
        self.assertEqual(textio._cjk_number_to_int("十二"), 12)
        self.assertEqual(textio._cjk_number_to_int("二十三"), 23)
        self.assertEqual(textio._cjk_number_to_int("一百"), 100)
        self.assertIsNone(textio._cjk_number_to_int("不是数字"))

    def test_the_reader_is_deterministic(self) -> None:
        text = fixtures._text_of(fixtures.NORMAL_LINES)
        first = read_text_document(text).as_dict()
        second = read_text_document(text).as_dict()
        self.assertEqual(first, second)


class EndToEndReproducibilityTests(unittest.TestCase):
    """The Skill's whole output must be stable run to run."""

    def _stable(self, payload: dict) -> dict:
        payload = json.loads(json.dumps(payload))
        payload.pop("invocation_id", None)
        payload.pop("started_at", None)
        payload.pop("finished_at", None)
        payload.get("producer", {}).pop("run_id", None)
        for unit in payload.get("units", []):
            unit.get("producer", {}).pop("run_id", None)
        return payload

    def test_repeated_runs_produce_identical_output(self) -> None:
        artifact = Artifact.from_file(fixtures.case_path("normal"), "art-normal")
        skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
        first = self._stable(skill.run(artifact, source_id="s").as_dict())
        second = self._stable(skill.run(artifact, source_id="s").as_dict())
        self.assertEqual(first, second)

    def test_repeated_runs_are_identical_for_every_case(self) -> None:
        skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
        for case in fixtures.CASES:
            with self.subTest(case=case):
                artifact = Artifact.from_file(
                    fixtures.case_path(case), f"art-{case}"
                )
                first = self._stable(skill.run(artifact, source_id="s").as_dict())
                second = self._stable(skill.run(artifact, source_id="s").as_dict())
                self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
