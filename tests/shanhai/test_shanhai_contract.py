"""V2.3 -- ``ShanHai.LegalTextEvidence`` contract tests.

One named test per required capability, plus the prohibitions, so
"it is implemented" is checkable by reading the test list.

Required: registered text TextArtifact input, explicit Skill call, ``TextRunResult``
output over ``TextEvidenceUnit``, provision/article extraction, exact location,
extracted text, producer, provenance state.

Prohibited: retrieval, ranking, FTS, RAG, embeddings, vector database, LLM QA,
agent, tool loop, canonical promotion, legal authority engine, workflow,
registry, auto discovery, plugin system, database abstraction, universal schema,
multimodal ontology -- and the Core changes that a text-specific unit class,
legal Core or universal citation model would require.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import _bootstrap  # noqa: E402

from skills.shanhai.contracts import TextArtifact, text_digest_bytes  # noqa: E402
from skills.shanhai.contracts import (  # noqa: E402
    TextCitationAddress,
    TextEvidenceUnit,
    TextLossKind,
    TextUnitClass,
)
from skills.shanhai.contracts import TextEvidenceSkill, TextRunResult, TextSupport  # noqa: E402
from skills.shanhai import (  # noqa: E402
    DEFAULT_OPTIONS,
    FakeTextBackend,
    FixtureTextBackend,
    ShanHaiLegalTextEvidence,
    StructuralCode,
    TextCitationSelector,
    TextDocument,
    resolve_text_citation,
    resolve_text_citation_across,
    unit_text_context,
    unit_text_provisions,
)
from fixtures.shanhai import build_text_fixtures as fixtures  # noqa: E402

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SKILLS_ROOT = PROJECT_ROOT / "skills"


def artifact_for(case: str, *, media_type: str | None = None) -> TextArtifact:
    path = fixtures.case_path(case)
    if media_type is None:
        return TextArtifact.from_file(path, f"art-{case}")
    return TextArtifact.from_file(path, f"art-{case}", media_type=media_type)


def run_case(case: str, **options):
    skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
    return skill.run(artifact_for(case), source_id="src-shanhai", options=options or None)


def content_units(result):
    return [u for u in result.units if unit_text_provisions(u)]


class Capability_1_InputTests(unittest.TestCase):
    """Required: a registered UTF-8 text/plain TextArtifact, read-only and offline."""

    def test_a_registered_text_artifact_is_accepted(self) -> None:
        artifact = TextArtifact.from_file(
            fixtures.case_path("normal"), "src-shanhai", media_type="text/plain"
        )
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id="src-shanhai"
        )
        self.assertTrue(result.units)
        self.assertFalse(result.diagnostics.has_fatal_error)

    def test_declared_text_plain_media_type_raises_no_warning(self) -> None:
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact_for("normal", media_type="text/plain"), source_id="src-shanhai"
        )
        codes = {w.code for w in result.diagnostics.warnings}
        self.assertNotIn("media_type_not_text", codes)

    def test_an_undeclared_media_type_is_warned_about(self) -> None:
        """A caller who declares nothing gets ``application/octet-stream``.

        ShanHai knows that ``.txt`` is ``text/plain``, so the undeclared case has
        to be constructed rather than implied by an extension the media-type
        table happens not to carry. Declaring nothing must not be read as
        declaring text.
        """
        path = fixtures.case_path("normal")
        artifact = TextArtifact(
            artifact_id="art-undeclared",
            digest=text_digest_bytes(path.read_bytes()),
            byte_length=path.stat().st_size,
            location=str(path),
        )
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact, source_id="src-shanhai"
        )
        codes = {w.code for w in result.diagnostics.warnings}
        self.assertIn("media_type_not_text", codes)

    def test_an_image_artifact_is_refused_not_read(self) -> None:
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact_for("normal", media_type="image/png"), source_id="src-shanhai"
        )
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertEqual(result.diagnostics.errors[0].code, "artifact_is_not_text")
        self.assertEqual(result.units, ())

    def test_digest_is_recorded_and_the_artifact_is_not_modified(self) -> None:
        path = fixtures.case_path("normal")
        before = path.read_bytes()
        result = run_case("normal")
        self.assertEqual(path.read_bytes(), before)
        for unit in result.units:
            self.assertEqual(unit.provenance, result.artifact.content_digest)

    def test_missing_source_identity_fails_closed(self) -> None:
        result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
            artifact_for("normal")
        )
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertEqual(result.diagnostics.errors[0].code, "missing_source_identity")


class Capability_2_SkillBoundaryTests(unittest.TestCase):
    """Required: an explicit Skill call producing TextRunResult over TextEvidenceUnit."""

    def test_the_skill_is_a_core_skill(self) -> None:
        self.assertIsInstance(ShanHaiLegalTextEvidence(FixtureTextBackend()), TextEvidenceSkill)

    def test_skill_identity_is_reported(self) -> None:
        result = run_case("normal")
        self.assertEqual(result.skill_id, "ShanHai.LegalTextEvidence")
        self.assertEqual(result.producer.skill_id, "ShanHai.LegalTextEvidence")
        self.assertTrue(result.producer.skill_version)

    def test_output_is_a_skill_result_over_evidence_units(self) -> None:
        result = run_case("normal")
        self.assertIsInstance(result, TextRunResult)
        self.assertTrue(result.units)
        self.assertTrue(all(isinstance(u, TextEvidenceUnit) for u in result.units))

    def test_backend_injection_is_explicit(self) -> None:
        document = TextDocument(text="", backend_id="fake.text")
        backend = FakeTextBackend(text="第一条 测试内容。\n")
        skill = ShanHaiLegalTextEvidence(backend)
        result = skill.run(artifact_for("normal"), source_id="src-shanhai")
        self.assertEqual(result.diagnostics.backend_id, "fake.text")
        self.assertEqual(backend.load_calls, 1)
        del document

    def test_backends_option_is_honoured(self) -> None:
        backend = FakeTextBackend(text="第一条 测试内容。\n")
        result = ShanHaiLegalTextEvidence().run(
            artifact_for("normal"),
            source_id="src-shanhai",
            options={"backends": [backend]},
        )
        self.assertEqual(result.diagnostics.backend_id, "fake.text")

    def test_no_registry_or_discovery_exists(self) -> None:
        skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
        candidates = skill._candidate_backends({})  # noqa: SLF001 - order is the contract
        self.assertEqual([b.backend_id for b in candidates], ["fixture.utf8-text"])

    def test_result_serialises_end_to_end(self) -> None:
        payload = json.loads(
            json.dumps(run_case("normal").as_dict(), ensure_ascii=False)
        )
        self.assertEqual(payload["skill_id"], "ShanHai.LegalTextEvidence")
        self.assertTrue(payload["units"])
        self.assertIn("diagnostics", payload)


class Capability_3_ExtractionTests(unittest.TestCase):
    """Required: provision/article units with exact location and text."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact, cls.result = None, run_case("normal")
        cls.truth = json.loads(
            (fixtures.TRUTH_DIR / "normal_truth.json").read_text(encoding="utf-8")
        )

    def test_every_article_becomes_a_unit(self) -> None:
        self.assertEqual(
            self.result.diagnostics.stats["provision_numbers"], [1, 2, 3, 4, 5]
        )
        self.assertEqual(len(content_units(self.result)), 5)

    def test_chapters_become_container_units(self) -> None:
        containers = [u for u in self.result.units if u.unit_class == TextUnitClass.CONTAINER]
        self.assertEqual(len(containers), 2)
        self.assertEqual(self.result.diagnostics.stats["chapter_count"], 2)

    def test_units_use_generic_core_classes_only(self) -> None:
        for unit in self.result.units:
            self.assertIn(unit.unit_class, TextUnitClass.ALL)

    def test_each_unit_carries_source_artifact_and_producer(self) -> None:
        for unit in content_units(self.result):
            self.assertEqual(unit.source_id, "src-shanhai")
            self.assertTrue(unit.artifact_id)
            self.assertEqual(unit.producer.skill_id, "ShanHai.LegalTextEvidence")
            self.assertEqual(unit.producer.backend_id, "fixture.utf8-text")

    def test_extracted_text_matches_the_fixture_exactly(self) -> None:
        """The recorded span must reproduce the recorded text, per the truth file."""
        by_number = {
            provision["number"]: provision for provision in self.truth["articles"]
        }
        for unit in content_units(self.result):
            provision = unit_text_provisions(unit)[0]
            expected = by_number[provision["number"]]
            with self.subTest(article=provision["number"]):
                self.assertEqual(provision["span"]["char_start"], expected["char_start"])
                self.assertEqual(provision["span"]["char_end"], expected["char_end"])
                self.assertEqual(provision["span"]["line_start"], expected["line_start"])
                self.assertEqual(provision["span"]["line_end"], expected["line_end"])
                self.assertEqual(provision["text"], expected["text"])

    def test_exact_location_is_recorded_in_three_coordinate_systems(self) -> None:
        provision = unit_text_provisions(content_units(self.result)[0])[0]
        span = provision["span"]
        for key in (
            "char_start",
            "char_end",
            "byte_start",
            "byte_end",
            "line_start",
            "line_end",
        ):
            self.assertIn(key, span)
        self.assertGreater(span["byte_end"], span["byte_start"])
        self.assertGreater(span["char_end"], span["char_start"])

    def test_byte_offsets_point_at_the_same_text_as_char_offsets(self) -> None:
        raw = fixtures.case_path("normal").read_bytes()
        for unit in content_units(self.result):
            provision = unit_text_provisions(unit)[0]
            span = provision["span"]
            with self.subTest(article=provision["number"]):
                self.assertEqual(
                    raw[span["byte_start"] : span["byte_end"]].decode("utf-8"),
                    provision["text"],
                )

    def test_provenance_state_is_recorded(self) -> None:
        for unit in content_units(self.result):
            self.assertNotEqual(unit.provenance, "provenance_unavailable")


class Capability_4_StructuralDiagnosticsTests(unittest.TestCase):
    """Required: the six structural conditions, kept distinct."""

    def test_empty_artifact_is_a_condition_not_a_success(self) -> None:
        result = run_case("empty")
        self.assertEqual(result.diagnostics.stats["structural_codes"], [StructuralCode.EMPTY_ARTIFACT])
        self.assertFalse(result.diagnostics.stats["parsed"])
        self.assertFalse(result.is_complete_success)
        self.assertEqual(len(result.units), 1)
        self.assertIn(TextLossKind.EMPTY, result.units[0].loss)

    def test_unsupported_structure_is_reported(self) -> None:
        result = run_case("unsupported_structure")
        self.assertEqual(
            result.diagnostics.stats["structural_codes"],
            [StructuralCode.UNSUPPORTED_STRUCTURE],
        )
        self.assertIn(TextLossKind.UNSUPPORTED, result.units[0].loss)

    def test_latin_headings_are_refused_rather_than_half_parsed(self) -> None:
        result = run_case("latin_headings")
        self.assertEqual(
            result.diagnostics.stats["structural_codes"],
            [StructuralCode.UNSUPPORTED_STRUCTURE],
        )
        self.assertEqual(result.diagnostics.stats["provision_numbers"], [])

    def test_missing_marker_and_malformed_marker_are_distinct(self) -> None:
        """Three states that a numbering gap would otherwise swallow.

        ``missing_marker`` is not decoration: the fixture carries ``第廿条``, a
        well-formed article marker whose numeral this reader cannot resolve.
        Reporting it as a gap would claim the article is absent when the truth is
        that the reader cannot read its number.
        """
        missing = run_case("missing_marker")
        gap = run_case("numbering_gap_no_marker")
        malformed = run_case("malformed_marker")
        self.assertEqual(
            missing.diagnostics.stats["structural_codes"],
            [StructuralCode.MISSING_MARKER],
        )
        self.assertEqual(
            gap.diagnostics.stats["structural_codes"],
            [StructuralCode.NUMBERING_GAP],
        )
        self.assertEqual(
            malformed.diagnostics.stats["structural_codes"],
            [StructuralCode.MALFORMED_MARKER],
        )
        self.assertNotIn(
            StructuralCode.NUMBERING_GAP,
            missing.diagnostics.stats["structural_codes"],
        )
        self.assertNotIn(
            StructuralCode.MALFORMED_MARKER,
            missing.diagnostics.stats["structural_codes"],
        )

    def test_a_clean_gap_is_not_a_missing_marker(self) -> None:
        result = run_case("numbering_gap_no_marker")
        self.assertEqual(result.diagnostics.stats["provision_numbers"], [1, 3])
        self.assertNotIn(
            StructuralCode.MISSING_MARKER,
            result.diagnostics.stats["structural_codes"],
        )

    def test_numbering_gap_is_reported_for_a_clean_gap(self) -> None:
        result = run_case("gap")
        self.assertEqual(result.diagnostics.stats["provision_numbers"], [1, 2, 5])
        self.assertEqual(
            result.diagnostics.stats["structural_codes"], [StructuralCode.NUMBERING_GAP]
        )
        self.assertFalse(result.is_complete_success)

    def test_duplicate_marker_is_reported(self) -> None:
        result = run_case("duplicate_marker")
        self.assertEqual(
            result.diagnostics.stats["provision_numbers"], [1, 2, 2, 3]
        )
        self.assertEqual(
            result.diagnostics.stats["structural_codes"], [StructuralCode.DUPLICATE_MARKER]
        )
        self.assertTrue(
            any("duplicate article marker" in w.message for w in result.diagnostics.warnings)
        )

    def test_extraction_failure_is_reported(self) -> None:
        result = run_case("not_utf8")
        self.assertEqual(
            result.diagnostics.stats["structural_codes"], [StructuralCode.ENCODING_FAILURE]
        )
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertIn(TextLossKind.FAILED, result.units[0].loss)

    def test_zero_units_never_means_success(self) -> None:
        """Every non-parsing case must be visibly unsuccessful."""
        for case in (
            "empty",
            "unsupported_structure",
            "latin_headings",
            "not_utf8",
            "missing_marker",
            "malformed_marker",
            "gap",
            "duplicate_marker",
        ):
            with self.subTest(case=case):
                result = run_case(case)
                self.assertFalse(
                    result.is_complete_success,
                    f"{case} must not be reported as a complete success",
                )
                self.assertTrue(result.units, f"{case} must still emit a unit")

    def test_a_clean_document_does_report_success(self) -> None:
        """The complement: a document with no condition at all is a success."""
        result = run_case("normal")
        self.assertTrue(result.is_complete_success)
        self.assertEqual(result.diagnostics.stats["structural_codes"], [])

    def test_structural_codes_are_a_closed_skill_side_vocabulary(self) -> None:
        self.assertEqual(
            set(StructuralCode.ALL),
            {
                "empty_artifact",
                "unsupported_structure",
                "missing_marker",
                "malformed_marker",
                "numbering_gap",
                "duplicate_marker",
                "encoding_failure",
            },
        )

    def test_every_structural_code_maps_onto_a_core_loss_kind(self) -> None:
        """ShanHai's vocabulary must not require Core to learn new words."""
        from skills.shanhai import loss_kinds_for

        for code in StructuralCode.ALL:
            with self.subTest(code=code):
                kinds = loss_kinds_for([code])
                self.assertEqual(len(kinds), 1)
                self.assertIn(kinds[0], TextLossKind.ALL)

    def test_worker_table_encoding_fixture_is_really_not_utf8(self) -> None:
        raw = fixtures.case_path("not_utf8").read_bytes()
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8")


class Capability_5_TextSpecificInformationStaysInTheSkillTests(unittest.TestCase):
    """The Core boundary: text concepts must not appear in Core."""

    def test_core_evidence_has_no_text_specific_accessor(self) -> None:
        for attribute in (
            "text_span",
            "article_number",
            "paragraph_context",
            "legal_structure",
            "text_context",
        ):
            with self.subTest(attribute=attribute):
                self.assertFalse(
                    hasattr(TextEvidenceUnit, attribute),
                    f"TextEvidenceUnit must not expose {attribute!r}: text context is a "
                    f"Skill-side convention, not a Core concept",
                )

    def test_core_citation_address_carries_axes_only_in_the_skill_payload(self) -> None:
        """Core records a coordinate-system name; the axes live in the payload."""
        import dataclasses

        fields = {f.name for f in dataclasses.fields(TextCitationAddress)}
        self.assertEqual(
            fields,
            {"kind", "value", "container_id", "container_label", "context_path"},
        )
        for forbidden in ("char_start", "byte_start", "line_start", "article_number"):
            self.assertNotIn(forbidden, fields)

    def test_the_skill_uses_a_core_coordinate_system_name(self) -> None:
        result = run_case("normal")
        for unit in content_units(result):
            self.assertEqual(unit.address.kind, "content_location")
        for unit in result.units:
            if unit.unit_class == TextUnitClass.CONTAINER:
                self.assertEqual(unit.address.kind, "container_location")

    def test_provision_coordinates_live_in_the_skill_payload(self) -> None:
        unit = content_units(run_case("normal"))[0]
        provision = unit_text_provisions(unit)[0]
        self.assertIn("char_start", provision["span"])
        # ...and not on Core's address.
        self.assertFalse(hasattr(unit.address, "char_start"))

    def test_the_skill_metadata_is_flagged_experimental(self) -> None:
        unit = content_units(run_case("normal"))[0]
        context = unit_text_context(unit)
        self.assertIsNotNone(context)
        assert context is not None
        self.assertTrue(context["experimental"])
        self.assertTrue(context["unfrozen"])

    def test_text_specific_types_live_in_this_skill_not_in_a_runtime(self) -> None:
        """ShanHai keeps its own text concepts; it borrows none from a runtime.

        This replaces an earlier check that asserted a shared Core had no
        text-specific accessor. ShanHai is now independent: the text-shaped
        vocabulary is *this package's*, so the check is that the contract is
        self-contained and named for the domain.
        """
        from skills.shanhai import contracts as shanhai_contracts

        for required in (
            "TextEvidenceUnit",
            "TextCitationAddress",
            "TextLossKind",
            "TextUnitClass",
            "TextEvidenceSkill",
            "TextRunResult",
        ):
            with self.subTest(name=required):
                self.assertTrue(
                    hasattr(shanhai_contracts, required),
                    f"ShanHai must own {required}",
                )

    def test_this_skill_does_not_import_a_private_runtime(self) -> None:
        """No module in this package may import ``core`` or ``app``.

        Checked by parsing the source rather than by importing, so the check
        holds even on a module whose import would fail.
        """
        import ast

        offenders = []
        for path in sorted(SKILLS_ROOT.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in ("core", "app"):
                            offenders.append(f"{path.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    root = (node.module or "").split(".")[0]
                    if not node.level and root in ("core", "app"):
                        offenders.append(f"{path.name}: from {node.module} import ...")
        self.assertEqual(offenders, [], f"ShanHai must be self-contained; found {offenders}")


class ProhibitionTests(unittest.TestCase):
    """The explicit do-not-implement list, checked against the source."""

    FORBIDDEN_MODULES = (
        "sqlite3",
        "sqlalchemy",
        "numpy",
        "pandas",
        "requests",
        "openai",
        "langchain",
        "chromadb",
        "faiss",
        "transformers",
        "whoosh",
        "rank_bm25",
        "sklearn",
    )
    FORBIDDEN_PACKAGES = ("luohai",)

    def _shanhai_sources(self):
        for path in sorted((SKILLS_ROOT / "shanhai").rglob("*.py")):
            if "__pycache__" not in str(path):
                yield path

    def test_no_forbidden_dependency_is_imported(self) -> None:
        offenders: list[str] = []
        for path in self._shanhai_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [(node.module or "").split(".")[0]]
                    if (node.module or "").startswith("skills.luohai"):
                        offenders.append(f"{path.name}: skills.luohai")
                else:
                    continue
                for name in names:
                    if name in self.FORBIDDEN_MODULES:
                        offenders.append(f"{path.name}: {name}")
        self.assertEqual(offenders, [], f"forbidden imports: {offenders}")

    def test_shanhai_does_not_import_luohai(self) -> None:
        """Independence asserted on the import graph, not on prose.

        Scanning raw text would flag any docstring that merely *mentions* the
        other Skill, which is noise; what matters is that no import edge exists
        in either direction.
        """
        offenders: list[str] = []
        for path in self._shanhai_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue  # relative import inside this package
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    root = name.split(".")[0]
                    if root == "luohai" or name.startswith("skills.luohai"):
                        offenders.append(f"{path.name}: {name}")
        self.assertEqual(
            offenders,
            [],
            "ShanHai must be independent of LuoHai; the two Skills share only Core",
        )

    def test_luohai_does_not_import_shanhai(self) -> None:
        """The other direction of the same guarantee."""
        offenders: list[str] = []
        for path in sorted((SKILLS_ROOT / "luohai").rglob("*.py")):
            if "__pycache__" in str(path):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    root = name.split(".")[0]
                    if root == "shanhai" or name.startswith("skills.shanhai"):
                        offenders.append(f"{path.name}: {name}")
        self.assertEqual(offenders, [], f"LuoHai imports ShanHai: {offenders}")

    def test_no_retrieval_ranking_or_search_machinery_is_defined(self) -> None:
        forbidden = (
            "retriev",
            "rank",
            "fts",
            "embed",
            "vectorstore",
            "vector_store",
            "similarity",
            "promote",
            "canonical",
            "authority",
            "workflow",
            "registry",
            "plugin",
        )
        offenders: list[str] = []
        for path in self._shanhai_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    lowered = node.name.lower()
                    for token in forbidden:
                        if token in lowered:
                            offenders.append(f"{path.name}: {node.name}")
        self.assertEqual(offenders, [], f"forbidden machinery defined: {offenders}")

    def test_default_options_contain_no_retrieval_style_switch(self) -> None:
        for key in DEFAULT_OPTIONS:
            lowered = key.lower()
            for token in ("rank", "retriev", "top_k", "score", "similar"):
                self.assertNotIn(token, lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
