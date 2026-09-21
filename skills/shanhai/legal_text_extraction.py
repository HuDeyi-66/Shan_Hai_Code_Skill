"""``ShanHai.LegalTextEvidence`` -- the second independent Skill.

Read-only legal-text evidence extraction from a registered UTF-8 text artifact.

This is the second Skill built on the sealed Core, and its purpose is to test
exactly that: whether a small modality-neutral Core can carry a second evidence
shape without being extended. It is **not** a rebuild of the historical ShanHai
runtime. There is no intake system, no owner gate, no promotion pipeline, no
source library, no CLI workflow and no repository-script dependency here.

Pipeline position
-----------------
::

    registered text Artifact
            |
        ShanHai Skill          (this module)
            |
        SkillResult
            |
        EvidenceUnit[]         (article and chapter units)
            |
        text citation reconstruction   (skills/shanhai/citation.py)

Where text-specific information lives
-------------------------------------
Core is sealed. It records a coordinate-system *name*, a container reference and
an opaque context path on ``CitationAddress``, and nothing modality-specific.
Everything text-shaped therefore lives in this Skill's payload:

* character / byte / line spans,
* article and chapter markers,
* paragraph spans,
* the six-way structural vocabulary.

There is no ``TextEvidenceUnit``, no ``LegalEvidenceCore`` and no
``UniversalCitationModel``. Those would be Core changes, and none are needed.

Evidence rules carried over unchanged
-------------------------------------
* **No silent success.** A run with zero units is never a success: an empty
  artifact, an unsupported structure and a decode failure each produce an
  explicit condition, and ``is_complete_success`` is False whenever anything was
  lost.
* **Distinct failure states.** ``empty_artifact``, ``unsupported_structure``,
  ``missing_marker``, ``malformed_marker``, ``numbering_gap``,
  ``duplicate_marker`` and ``encoding_failure`` are never conflated. Each maps
  to a Core loss kind and keeps its own code in the payload.
* **No first match, no ordering guess, no fuzzy match.** A duplicated marker
  yields ``ambiguous`` from the resolver, never a choice.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from core.artifact import Artifact, digest_bytes
from core.evidence import (
    CitationAddress,
    EvidenceUnit,
    LossKind,
    ProducerRef,
    UnitClass,
)
from core.skill_result import (
    Capability,
    RunDiagnostics,
    Skill,
    SkillResult,
    Support,
)

from .backends import TEXT_MEDIA_TYPES, FixtureTextBackend, TextBackend
from .textio import (
    StructuralCode,
    TextDocument,
    TextProvision,
    loss_kinds_for,
    structural_loss_kind,
)

__all__ = ["ShanHaiLegalTextEvidence", "DEFAULT_OPTIONS", "SHANHAI_METADATA_KEY"]

#: Where this Skill attaches its private context on a unit's ``metadata``.
#: A convention between this package and the units it writes -- Core neither
#: knows nor requires it.
SHANHAI_METADATA_KEY = "shanhai"

#: Options this Skill understands. There is deliberately **no** truncation knob.
#:
#: An earlier revision offered ``max_provisions``, which sliced the provision list
#: and merely warned. That is silent content omission wearing a warning label: the
#: document-level loss never reached the units, so ``is_complete_success`` stayed
#: true for a result that did not contain the document. A bounded reader that can
#: drop content is not evidence, so the option is gone rather than repaired --
#: there is no caller-selectable way to make this Skill return less than it found.
#:
#: ``fail_closed`` is also absent. LuoHai declares it because its reader chain can
#: retry another backend after a fatal observation; this reader never falls back at
#: all (candidate selection is availability-based and a fatal read is terminal), so
#: the switch would name behaviour the Skill does not have.
DEFAULT_OPTIONS: Mapping[str, Any] = {
    "backends": None,
    "emit_chapter_units": True,
}

_SKILL_CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        name="legal_text_evidence_units",
        support=Support.SUPPORTED,
        detail="one EvidenceUnit per detected article, plus container units for "
               "chapters or, when nothing was detected, for the document",
    ),
    Capability(
        name="structural_diagnostics",
        support=Support.SUPPORTED,
        detail="empty_artifact, unsupported_structure, missing_marker, "
               "malformed_marker, numbering_gap and duplicate_marker are kept "
               "distinct and never conflated",
    ),
    Capability(
        name="exact_span_location",
        support=Support.SUPPORTED,
        detail="character, UTF-8 byte and 1-based line spans recorded per "
               "provision, computed from the artifact bytes",
    ),
    Capability(
        name="text_citation_reconstruction",
        support=Support.SUPPORTED,
        detail="an article, a paragraph or a character span rebuilds to an exact, "
               "verifiable text location; duplicates return ambiguity",
    ),
    Capability(
        name="paragraph_split",
        support=Support.PARTIAL,
        detail="paragraphs are blank-line separated blocks inside an article",
    ),
    Capability(
        name="retrieval_or_ranking",
        support=Support.UNSUPPORTED,
        detail="no retrieval, ranking, FTS, similarity or fuzzy matching exists "
               "in this Skill by design",
    ),
    Capability(
        name="ocr_and_non_text",
        support=Support.UNSUPPORTED,
        detail="only UTF-8 text is read; images, PDFs and binary formats are not "
               "text artifacts",
    ),
    Capability(
        name="legal_authority",
        support=Support.UNSUPPORTED,
        detail="this Skill records where text is; it makes no claim about whether "
               "the text is authoritative, current or legally effective",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class _BackendChoice:
    backend: TextBackend


class ShanHaiLegalTextEvidence(Skill):
    """Extract provisional EvidenceUnits from a UTF-8 legal text artifact.

    Parameters
    ----------
    backend:
        Explicit backend injection. When omitted, ``options['backends']`` is
        consulted; when that is absent too, the deterministic stdlib
        :class:`~skills.shanhai.backends.FixtureTextBackend` is used. There is no
        scanning and no auto-discovery: wiring is always explicit.
    """

    skill_id = "ShanHai.LegalTextEvidence"
    skill_version = "0.1.0-provisional"

    def __init__(
        self,
        backend: TextBackend | None = None,
        *,
        backends: Sequence[TextBackend] | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> None:
        self._explicit_backend = backend
        self._backends = tuple(backends) if backends is not None else None
        self._defaults = {**DEFAULT_OPTIONS, **dict(options or {})}

    # -- capability ------------------------------------------------------

    def capabilities(self) -> tuple[Capability, ...]:
        caps = list(_SKILL_CAPABILITIES)
        seen: set[tuple[str, str]] = set()
        for backend in self._candidate_backends({}):
            for capability in backend.capabilities():
                key = (backend.backend_id, capability.name)
                if key in seen:
                    continue
                seen.add(key)
                caps.append(
                    Capability(
                        name=f"{backend.backend_id}:{capability.name}",
                        support=capability.support,
                        detail=capability.detail,
                        collapse_risks=capability.collapse_risks,
                    )
                )
        return tuple(caps)

    # -- run -------------------------------------------------------------

    def run(
        self,
        artifact: Artifact,
        *,
        source_id: str | None = None,
        options: Mapping[str, Any] | None = None,
        source: Any = None,
    ) -> SkillResult:
        resolved_source_id = source_id or getattr(source, "source_id", None)
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        started_at = _utc_now()
        merged = {**self._defaults, **dict(options or {})}
        diagnostics = RunDiagnostics(options_echo=dict(options or {}))
        producer = ProducerRef(
            skill_id=self.skill_id,
            skill_version=self.skill_version,
            run_id=run_id,
            method="read_only_extract",
        )

        if not resolved_source_id:
            diagnostics.error(
                "missing_source_identity",
                "no source identity was supplied; evidence units cannot be "
                "traced to a registered source",
                fatal=True,
            )
            return self._finish(
                artifact, producer, diagnostics, run_id, started_at, ()
            )

        path = artifact.location
        if not path:
            diagnostics.error(
                "artifact_has_no_location",
                "artifact carries no readable location; nothing can be read",
                fatal=True,
            )
            return self._finish(
                artifact, producer, diagnostics, run_id, started_at, ()
            )

        if artifact.media_type not in TEXT_MEDIA_TYPES:
            if artifact.media_type.startswith("image/") or artifact.media_type.endswith(
                "pdf"
            ):
                diagnostics.error(
                    "artifact_is_not_text",
                    f"artifact media type is {artifact.media_type!r}; this Skill "
                    f"reads UTF-8 text only and performs no OCR",
                    fatal=True,
                )
                return self._finish(
                    artifact, producer, diagnostics, run_id, started_at, ()
                )
            diagnostics.warn(
                "media_type_not_text",
                f"artifact media type is {artifact.media_type!r}; this Skill "
                f"claims {list(TEXT_MEDIA_TYPES)}",
                scope=artifact.artifact_id,
            )

        choice = self._select_backend(merged, diagnostics)

        # ARTIFACT INTEGRITY GATE. Verified before a single byte is decoded.
        #
        # Evidence that points at an artifact whose digest does not match the
        # registered record is not evidence: the citation would be structurally
        # correct and bound to unverified bytes, and every unit would carry a
        # digest that was never true of what was read. A mismatch is therefore
        # fatal, produces no units, and names both digests so the discrepancy is
        # attributable rather than merely reported.
        integrity_problem = self._verify_artifact_bytes(artifact, path)
        if integrity_problem is not None:
            diagnostics.error(
                "artifact_integrity_mismatch",
                integrity_problem,
                scope=artifact.artifact_id,
                fatal=True,
            )
            diagnostics.stats = {
                "unit_count": 0,
                "provision_count": 0,
                "provision_numbers": [],
                "chapter_count": 0,
                "structural_codes": [],
                "classification": "unverified",
                "parsed": False,
                "integrity_verified": False,
            }
            return self._finish(
                artifact, producer, diagnostics, run_id, started_at, ()
            )

        document = self._safe_load(choice.backend, path, merged, diagnostics)
        units = self._build_units(
            artifact=artifact,
            source_id=resolved_source_id,
            document=document,
            producer=producer,
            merged=merged,
            diagnostics=diagnostics,
            backend=choice.backend,
        )

        # ZERO-UNIT INVARIANT. Every path above either emits at least one unit or
        # fails closed; this is the backstop that makes the invariant true for
        # the whole run rather than for the paths we happened to think of. A run
        # that returns no units is a failure, never a clean success.
        if not units:
            diagnostics.error(
                "zero_units_emitted",
                "the run produced no evidence units; an empty result is treated "
                "as a failure because it cannot be distinguished from a complete "
                "extraction failure by a caller",
                scope=artifact.artifact_id,
                fatal=True,
            )
            diagnostics.stats = {
                "unit_count": 0,
                "provision_count": 0,
                "provision_numbers": [],
                "chapter_count": 0,
                "structural_codes": [
                    code for code, _ in document.structural_findings
                ],
                "classification": document.classification,
                "parsed": False,
                "integrity_verified": True,
            }
            return self._finish(
                artifact, producer, diagnostics, run_id, started_at, ()
            )

        self._record_diagnostics(document, choice.backend, diagnostics, units)
        diagnostics.stats["integrity_verified"] = True
        return self._finish(
            artifact, producer, diagnostics, run_id, started_at, units
        )

    @staticmethod
    def _verify_artifact_bytes(artifact: Artifact, path: str) -> str | None:
        """Re-read the artifact and compare it with the recorded digest.

        Returns a problem description, or ``None`` when the bytes match. The bytes
        are read once here and the backend reads them again; the duplicate read is
        deliberate, because it keeps the gate independent of whatever the backend
        does with the file.
        """
        try:
            with open(path, "rb") as handle:
                payload = handle.read()
        except OSError as exc:
            return (
                f"artifact is unreadable, so its integrity cannot be verified: {exc}"
            )
        try:
            matches = artifact.verify_bytes(payload)
        except Exception as exc:  # noqa: BLE001 - a bad digest is a result, not a crash
            return f"artifact digest could not be checked: {exc}"
        if matches:
            return None
        return (
            f"artifact bytes do not match the recorded digest: expected "
            f"{artifact.content_digest}, observed "
            f"{artifact.digest_algorithm}:{digest_bytes(payload, artifact.digest_algorithm)}. "
            f"Nothing was extracted, because evidence bound to unverified bytes "
            f"cannot be cited."
        )

    # -- backend selection -----------------------------------------------

    def _candidate_backends(
        self, options: Mapping[str, Any]
    ) -> tuple[TextBackend, ...]:
        if self._explicit_backend is not None:
            return (self._explicit_backend,)
        if self._backends is not None:
            return self._backends
        injected = options.get("backends")
        if injected:
            return tuple(injected)
        # One backend only. There is no OSS text backend to prefer or fall back
        # from, and inventing a second candidate purely to have a fallback would
        # add a code path with no evidence behind it.
        return (FixtureTextBackend(),)

    def _select_backend(
        self, options: Mapping[str, Any], diagnostics: RunDiagnostics
    ) -> _BackendChoice:
        candidates = self._candidate_backends(options)
        diagnostics.considered_backends = [b.backend_id for b in candidates]
        for backend in candidates:
            if backend.is_available():
                return _BackendChoice(backend=backend)
        diagnostics.error(
            "no_backend_available",
            "no candidate text backend is usable: "
            + ", ".join(b.backend_id for b in candidates),
            fatal=True,
        )
        diagnostics.unsupported_capabilities.append("utf8_text_read")
        return _BackendChoice(backend=candidates[-1])

    def _safe_load(
        self,
        backend: TextBackend,
        path: str,
        options: Mapping[str, Any],
        diagnostics: RunDiagnostics,
    ) -> TextDocument:
        """Call ``backend.load`` and turn an exception into evidence.

        Only ``Exception`` is caught. A ``BaseException`` subclass must be
        contained by its own adapter, because swallowing it here would also
        swallow process-level interruption.
        """
        try:
            return backend.load(path, options)
        except Exception as exc:  # noqa: BLE001 - converted into diagnostics
            problem = f"{type(exc).__name__}: {exc}"
            diagnostics.error(
                "backend_raised",
                f"backend {backend.backend_id!r} raised an unexpected exception: "
                f"{problem}",
                scope=backend.backend_id,
                fatal=True,
            )
            return TextDocument(
                text="",
                loss=(LossKind.FAILED,),
                errors=(f"backend_raised: {problem}",),
                fatal=True,
                backend_id=backend.backend_id,
                backend_version=backend.backend_version,
                backend_path=backend.backend_path,
            )

    # -- evidence construction -------------------------------------------

    def _producer_for(
        self, producer: ProducerRef, backend: TextBackend
    ) -> ProducerRef:
        return ProducerRef(
            skill_id=producer.skill_id,
            skill_version=producer.skill_version,
            backend_id=backend.backend_id,
            backend_version=backend.backend_version,
            run_id=producer.run_id,
            method=producer.method,
        )

    def _build_units(
        self,
        *,
        artifact: Artifact,
        source_id: str,
        document: TextDocument,
        producer: ProducerRef,
        merged: Mapping[str, Any],
        diagnostics: RunDiagnostics,
        backend: TextBackend,
    ) -> tuple[EvidenceUnit, ...]:
        for code, detail in document.structural_findings:
            diagnostics.warn(f"structure:{code}", detail, scope=artifact.artifact_id)
        for warning in document.warnings:
            diagnostics.warn("text_warning", warning, scope=artifact.artifact_id)

        unit_producer = self._producer_for(producer, backend)

        # A document that produced no provisions still yields one unit, so that
        # the condition is visible in the units and not only in diagnostics. A
        # run returning zero units must never read as an empty success.
        if not document.provisions:
            return (
                self._document_unit(
                    artifact=artifact,
                    source_id=source_id,
                    document=document,
                    producer=unit_producer,
                ),
            )

        # No truncation. Every detected provision becomes a unit; there is no
        # option that returns less than the document contains. The only way a
        # provision is missing from ``units`` is that the reader did not detect it,
        # and that is reported as a structural condition instead of being applied
        # as a silent slice.
        #
        # ``order`` is the 1-based position among detected elements and is part of
        # the unit handle. Two occurrences of the same article number are two
        # distinct pieces of evidence and must not share an identity; the number
        # alone is a *label*, not a key. Citations still resolve by label and
        # return ambiguity, so uniqueness here never silently picks a winner.
        units: list[EvidenceUnit] = []
        if merged.get("emit_chapter_units", True):
            for order, (number, marker, span) in enumerate(document.chapters, start=1):
                units.append(
                    self._chapter_unit(
                        artifact=artifact,
                        source_id=source_id,
                        document=document,
                        number=number,
                        marker=marker,
                        span=span,
                        order=order,
                        producer=unit_producer,
                    )
                )
        for order, provision in enumerate(document.provisions, start=1):
            units.append(
                self._provision_unit(
                    artifact=artifact,
                    source_id=source_id,
                    document=document,
                    provision=provision,
                    order=order,
                    producer=unit_producer,
                )
            )
        return tuple(units)

    def _provision_payload(
        self, document: TextDocument, provision: TextProvision
    ) -> dict[str, Any]:
        return {
            "provision_id": provision.provision_id,
            "number": provision.number,
            "marker": provision.marker,
            "heading": provision.heading,
            "chapter_number": provision.chapter_number,
            "chapter_marker": provision.chapter_marker,
            "text": provision.text,
            "text_length": len(provision.text),
            "span": provision.span.as_dict(),
            "paragraph_spans": [s.as_dict() for s in provision.paragraph_spans],
            "paragraph_count": provision.paragraphs,
            "numbers_in_marker_form": list(provision.numbers_in_marker_form),
            "malformed": provision.malformed,
            "malformed_reason": provision.malformed_reason,
            "malformed_code": provision.malformed_code,
            "document_classification": document.classification,
        }

    def _context_header(self, document: TextDocument) -> dict[str, Any]:
        """The *generic* part of the Skill-side context.

        Goes into ``unit.metadata``, which is Core's generic escape hatch, so a
        consumer can read document-level facts without knowing ShanHai's private
        payload shape. The provision records themselves go into ``unit.payload``
        separately -- mixing the two would make the modality-neutral part
        indistinguishable from the text-specific part.
        """
        return {
            "experimental": True,
            "unfrozen": True,
            "document": {
                "title": document.title,
                "classification": document.classification,
                "char_count": document.char_count,
                "byte_count": document.byte_count,
                "line_count": document.line_count,
            },
            "structural_findings": [
                {"code": code, "detail": detail}
                for code, detail in document.structural_findings
            ],
            "structural_codes": [code for code, _ in document.structural_findings],
        }

    def _text_payload(
        self, document: TextDocument, provisions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """The *modality-specific* part of the context, for ``unit.payload``."""
        payload = self._context_header(document)
        payload["provisions"] = provisions
        return payload

    def _provision_unit(
        self,
        *,
        artifact: Artifact,
        source_id: str,
        document: TextDocument,
        provision: TextProvision,
        order: int,
        producer: ProducerRef,
    ) -> EvidenceUnit:
        # Loss is per-unit. A document-level condition elsewhere -- a numbering
        # gap, a duplicated marker, a malformed marker in another article -- is
        # reported on the document and in diagnostics, and it does NOT mark a
        # clean article as lossy. Attaching every document condition to every
        # unit would make an unrelated condition block a perfectly good citation,
        # which over-reports rather than under-reports but is still wrong.
        loss: list[str] = []
        if provision.malformed:
            # The unit's loss kind is derived from the code the reader actually
            # recorded for this provision, not from a blanket "malformed" guess.
            # The reader's two provisional-article paths are both
            # ``missing_marker`` (a well-formed marker whose numeral cannot be
            # read); mapping them to FAILED would report a different condition at
            # unit level than the document reports, which is the conflation this
            # vocabulary exists to prevent.
            code = provision.malformed_code or StructuralCode.MALFORMED_MARKER
            loss.append(structural_loss_kind(code) or LossKind.FAILED)

        context = self._context_header(document)
        payload = self._text_payload(
            document, [self._provision_payload(document, provision)]
        )

        context_path = [f"document:{document.title or artifact.artifact_id}"]
        if provision.chapter_number is not None:
            context_path.append(f"chapter:{provision.chapter_number}")
        context_path.append(f"article:{provision.number}")
        context_path.append(f"span:{provision.span.char_ref}")

        number_label = provision.number if provision.number > 0 else "unparsed"
        return EvidenceUnit(
            # ``order`` disambiguates repeated article numbers; ``number_label``
            # keeps the handle readable and stable for the ordinary case, where
            # order and label agree by construction.
            unit_id=f"{artifact.artifact_id}:article:{order}:{number_label}",
            unit_class=UnitClass.CONTENT,
            source_id=source_id,
            artifact_id=artifact.artifact_id,
            producer=producer,
            address=CitationAddress(
                kind="content_location",
                value=provision.provision_id,
                container_id=f"article:{number_label}",
                container_label=provision.heading or provision.marker,
                context_path=tuple(context_path),
            ),
            content={
                "provision_id": provision.provision_id,
                "marker": provision.marker,
                "heading": provision.heading,
                "text": provision.text,
                "span": provision.span.as_dict(),
                "paragraph_count": provision.paragraphs,
            },
            content_raw=provision.span.extract(document.text),
            content_rendered=provision.text,
            provenance=artifact.content_digest,
            loss=tuple(dict.fromkeys(loss)),
            self_warnings=(
                (
                    f"marker {provision.marker!r} could not be resolved "
                    f"({code}: {provision.malformed_reason})",
                )
                if provision.malformed
                else ()
            ),
            payload={SHANHAI_METADATA_KEY: payload},
            metadata={SHANHAI_METADATA_KEY: context},
        )

    def _chapter_unit(
        self,
        *,
        artifact: Artifact,
        source_id: str,
        document: TextDocument,
        number: int,
        marker: str,
        span: Any,
        order: int,
        producer: ProducerRef,
    ) -> EvidenceUnit:
        members = [
            p.number for p in document.provisions if p.chapter_number == number
        ]
        context = self._context_header(document)
        payload = self._text_payload(document, [])
        payload["chapter"] = {
            "number": number,
            "marker": marker,
            "span": span.as_dict(),
            "article_numbers": members,
        }
        return EvidenceUnit(
            unit_id=f"{artifact.artifact_id}:chapter:{order}:{number}",
            unit_class=UnitClass.CONTAINER,
            source_id=source_id,
            artifact_id=artifact.artifact_id,
            producer=producer,
            address=CitationAddress(
                kind="container_location",
                value=f"chapter:{number}",
                container_id=f"chapter:{number}",
                container_label=marker,
                context_path=(f"document:{document.title or artifact.artifact_id}", f"chapter:{number}"),
            ),
            content={
                "chapter_number": number,
                "marker": marker,
                "article_numbers": members,
                "span": span.as_dict(),
            },
            # A container unit records the text at its own span, so that the
            # chapter heading is present in the evidence rather than only as
            # coordinates. It still carries no provision payload: a container is
            # a location, not a citation target.
            content_raw=span.extract(document.text),
            provenance=artifact.content_digest,
            # A chapter is a container, so it reflects the document's own
            # conditions; individual articles do not inherit them.
            loss=tuple(document.loss),
            payload={SHANHAI_METADATA_KEY: payload},
            metadata={SHANHAI_METADATA_KEY: context},
        )

    def _document_unit(
        self,
        *,
        artifact: Artifact,
        source_id: str,
        document: TextDocument,
        producer: ProducerRef,
    ) -> EvidenceUnit:
        """The single unit emitted when no provision could be detected.

        This is where ``empty_artifact``, ``unsupported_structure`` and
        ``encoding_failure`` become visible in the evidence itself rather than
        only in diagnostics.
        """
        codes = [code for code, _ in document.structural_findings]
        loss = list(document.loss)
        if not loss:
            loss.append(LossKind.EMPTY)

        context = self._context_header(document)
        payload = self._text_payload(document, [])

        return EvidenceUnit(
            unit_id=f"{artifact.artifact_id}:document",
            unit_class=UnitClass.CONTAINER,
            source_id=source_id,
            artifact_id=artifact.artifact_id,
            producer=producer,
            address=CitationAddress(
                kind="container_location",
                value="document",
                container_id="document",
                container_label=document.title,
                context_path=(f"document:{document.title or artifact.artifact_id}",),
            ),
            content={
                "classification": document.classification,
                "structural_codes": codes,
                "char_count": document.char_count,
                "byte_count": document.byte_count,
                "line_count": document.line_count,
            },
            provenance=artifact.content_digest,
            loss=tuple(dict.fromkeys(loss)),
            self_warnings=tuple(detail for _, detail in document.structural_findings),
            self_errors=document.errors,
            payload={SHANHAI_METADATA_KEY: payload},
            metadata={SHANHAI_METADATA_KEY: context},
        )

    # -- diagnostics -----------------------------------------------------

    def _record_diagnostics(
        self,
        document: TextDocument,
        backend: TextBackend,
        diagnostics: RunDiagnostics,
        units: Sequence[EvidenceUnit],
    ) -> None:
        diagnostics.backend_id = backend.backend_id
        diagnostics.backend_version = backend.backend_version
        diagnostics.backend_path = backend.backend_path
        diagnostics.known_collapse_risks = []
        diagnostics.observed_loss_kinds = sorted(
            {kind for unit in units for kind in unit.loss}
            or set(document.loss)
        )

        for error in document.errors:
            diagnostics.error(
                "text_backend_error",
                error,
                scope=backend.backend_id,
                fatal=document.fatal,
            )

        # There is deliberately no "no units emitted" warning here. An earlier
        # revision warned when the backend returned nothing, which the V2.3 review
        # rejected: a warning is not a loss assessment, and it left an empty
        # result readable as success. The zero-unit invariant is enforced at run
        # level, where it fails closed, so this method is only ever reached with
        # at least one unit.
        for capability in self.capabilities():
            if capability.support in (Support.UNSUPPORTED, Support.PARTIAL):
                if capability.name not in diagnostics.unsupported_capabilities:
                    diagnostics.unsupported_capabilities.append(capability.name)

        codes = [code for code, _ in document.structural_findings]
        diagnostics.stats = {
            "unit_count": len(units),
            "provision_count": len(document.provisions),
            "provision_numbers": [p.number for p in document.provisions],
            "chapter_count": len(document.chapters),
            "structural_codes": codes,
            "classification": document.classification,
            "char_count": document.char_count,
            "byte_count": document.byte_count,
            "line_count": document.line_count,
            "parsed": bool(document.provisions),
        }

    def _finish(
        self,
        artifact: Artifact,
        producer: ProducerRef,
        diagnostics: RunDiagnostics,
        run_id: str,
        started_at: str,
        units: Sequence[EvidenceUnit],
    ) -> SkillResult:
        return SkillResult(
            artifact=artifact,
            skill_id=self.skill_id,
            producer=producer,
            units=tuple(units),
            diagnostics=diagnostics,
            invocation_id=run_id,
            started_at=started_at,
            finished_at=_utc_now(),
        )
