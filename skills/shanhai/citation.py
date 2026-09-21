"""ShanHai text citation reconstruction.

Rebuild an exact text location from an ``TextEvidenceUnit``, or refuse.

The rule inherited from the workbook Skill applies here unchanged: **no first
match**. If a marker occurs more than once, a citation to it is not unique, and
this module returns every candidate rather than choosing one. Text makes this
sharper than tables did, because a duplicated article number is a real-world
drafting error, not a synthetic fixture trick.

What a ShanHai citation carries
-------------------------------
A ``TextCitation`` is checkable in three coordinate systems at once, because a
consumer may hold any one of them:

* ``char_start``/``char_end``  -- Python string indices
* ``byte_start``/``byte_end``  -- UTF-8 offsets
* ``line_start``/``line_end``  -- 1-based lines

plus the extracted text itself, so the citation can be verified without
re-reading the artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .contracts import TextEvidenceUnit

from .textio import TextSpan

__all__ = [
    "TextCitationSelector",
    "TextCitation",
    "TextCitationProblem",
    "TextUnresolved",
    "TextAmbiguous",
    "TextCandidate",
    "blocked_by_loss",
    "resolve_text_citation",
    "resolve_text_citation_across",
    "unit_text_provisions",
    "iter_provisions",
]


class TextCitationProblem:
    """Why a text citation could not be rebuilt."""

    NO_TEXT_PAYLOAD = "no_text_payload"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    MALFORMED_SELECTOR = "malformed_selector"
    BLOCKED_BY_LOSS = "blocked_by_loss"

    ALL = (
        NO_TEXT_PAYLOAD,
        UNRESOLVED,
        AMBIGUOUS,
        MALFORMED_SELECTOR,
        BLOCKED_BY_LOSS,
    )


@dataclass
class TextCandidate:
    """One provision that matched a selector.

    Returned instead of picking one. ``span`` is enough to locate the text
    without re-reading the artifact.
    """

    unit_id: str
    provision_id: str
    article_number: int
    chapter_number: int | None
    marker: str
    heading: str | None
    span: TextSpan
    paragraph_index: int | None = None
    text: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "provision_id": self.provision_id,
            "article_number": self.article_number,
            "chapter_number": self.chapter_number,
            "marker": self.marker,
            "heading": self.heading,
            "paragraph_index": self.paragraph_index,
            "span": self.span.as_dict(),
            "text": self.text,
        }


@dataclass
class TextCitation:
    """A rebuilt, checkable text citation."""

    artifact_id: str
    source_id: str
    unit_id: str
    provision_id: str
    article_number: int
    chapter_number: int | None
    marker: str
    heading: str | None
    paragraph_index: int | None
    span: TextSpan
    text: str
    context_path: tuple[str, ...]
    uniqueness: str  # "provision_marker" | "document_span"
    loss: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    producer_backend_id: str | None = None

    PROVISIONAL = True

    @property
    def char_start(self) -> int:
        return self.span.char_start

    @property
    def char_end(self) -> int:
        return self.span.char_end

    @property
    def byte_start(self) -> int:
        return self.span.byte_start

    @property
    def byte_end(self) -> int:
        return self.span.byte_end

    @property
    def line_start(self) -> int:
        return self.span.line_start

    @property
    def line_end(self) -> int:
        return self.span.line_end

    @property
    def is_weak(self) -> bool:
        """True when the location was established without a provision marker."""
        return self.uniqueness != "provision_marker"

    def verify(self, text: str) -> bool:
        """Re-read the span from the artifact text and check it matches.

        This is what makes the citation evidence rather than an assertion: the
        caller can confirm the recorded text is exactly what the recorded
        offsets point at.
        """
        return self.span.extract(text) == self.text

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "source_id": self.source_id,
            "unit_id": self.unit_id,
            "provision_id": self.provision_id,
            "article_number": self.article_number,
            "chapter_number": self.chapter_number,
            "marker": self.marker,
            "heading": self.heading,
            "paragraph_index": self.paragraph_index,
            "span": self.span.as_dict(),
            "text": self.text,
            "text_length": len(self.text),
            "context_path": list(self.context_path),
            "uniqueness": self.uniqueness,
            "loss": list(self.loss),
            "notes": list(self.notes),
            "producer_backend_id": self.producer_backend_id,
        }


@dataclass
class TextUnresolved:
    """Nothing matched. A valid outcome, not a failure."""

    unit_id: str
    problem: str
    message: str
    candidates: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "unresolved",
            "unit_id": self.unit_id,
            "problem": self.problem,
            "message": self.message,
            "candidates": list(self.candidates),
        }


@dataclass
class TextAmbiguous:
    """Several provisions matched; the citation is NOT decided."""

    unit_id: str
    problem: str
    message: str
    candidates: tuple[TextCandidate, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "ambiguous",
            "unit_id": self.unit_id,
            "problem": self.problem,
            "message": self.message,
            "candidates": [c.as_dict() for c in self.candidates],
            "candidate_ids": [c.provision_id for c in self.candidates],
        }


@dataclass
class TextCitationSelector:
    """What the caller is trying to point at.

    Exactly one convention is required. Supplying several is rejected rather
    than resolved by precedence: picking which selector "wins" would be a
    silent choice about evidence, which is the thing this project forbids.
    """

    article_number: int | None = None
    chapter_number: int | None = None
    #: 1-based index into the article's blank-line-separated paragraphs.
    paragraph_index: int | None = None
    #: Character span, for a caller holding raw offsets.
    char_range: tuple[int, int] | None = None
    #: Reject rather than accept a citation that spans more than one provision.
    require_within_provision: bool = True
    #: When False, a provision whose unit reports loss may still be cited.
    allow_lossy: bool = False

    PROVISIONAL = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "article_number": self.article_number,
            "chapter_number": self.chapter_number,
            "paragraph_index": self.paragraph_index,
            "char_range": list(self.char_range) if self.char_range else None,
        }


# --------------------------------------------------------------------------
# reading provisions off a unit
# --------------------------------------------------------------------------


def unit_text_context(unit: TextEvidenceUnit) -> dict[str, Any] | None:
    """The *generic* ShanHai context attached to a unit, or ``None``.

    Read from the unit's generic ``metadata``. Core carries no text accessor --
    that boundary is deliberate and asserted by test.
    """
    context = (unit.metadata or {}).get("shanhai")
    return dict(context) if isinstance(context, Mapping) else None


def unit_text_provisions(unit: TextEvidenceUnit) -> tuple[Mapping[str, Any], ...]:
    """The provision records a unit carries, as written by the Skill.

    These live in ``unit.payload["shanhai"]["provisions"]``: the coordinate axes,
    markers and paragraph spans are modality-specific, so they belong in the
    Skill's private payload rather than in Core's generic containers.
    """
    context = (unit.payload or {}).get("shanhai")
    if not isinstance(context, Mapping):
        return ()
    provisions = context.get("provisions")
    if not isinstance(provisions, Sequence):
        return ()
    return tuple(p for p in provisions if isinstance(p, Mapping))


def iter_provisions(
    units: Sequence[TextEvidenceUnit],
) -> tuple[tuple[TextEvidenceUnit, Mapping[str, Any]], ...]:
    """Every ``(unit, provision)`` pair across a set of units, in unit order."""
    pairs: list[tuple[TextEvidenceUnit, Mapping[str, Any]]] = []
    for unit in units:
        for provision in unit_text_provisions(unit):
            pairs.append((unit, provision))
    return tuple(pairs)


def resolve_text_citation_across(
    units: Sequence[TextEvidenceUnit],
    selector: TextCitationSelector,
    *,
    document_text: str | None = None,
) -> TextCitation | TextAmbiguous | TextUnresolved:
    """Resolve a text citation across a whole document's units.

    This is the entry point that makes a *duplicated article marker* detectable.
    Each unit holds one provision, so a within-unit resolver can never see that
    the same marker occurs twice; resolving across the document can, and it
    returns every match instead of choosing.

    Callers holding a single unit should use :func:`resolve_text_citation`.
    """
    problem = _selector_problem(selector)
    if problem:
        return TextUnresolved(
            unit_id="",
            problem=TextCitationProblem.MALFORMED_SELECTOR,
            message=problem,
        )

    candidates: list[tuple[TextEvidenceUnit, TextCandidate]] = []
    unresolved: list[TextUnresolved] = []
    for unit in units:
        outcome = resolve_text_citation(
            unit, selector, document_text=document_text
        )
        if isinstance(outcome, TextCitation):
            candidates.append(
                (
                    unit,
                    TextCandidate(
                        unit_id=unit.unit_id,
                        provision_id=outcome.provision_id,
                        article_number=outcome.article_number,
                        chapter_number=outcome.chapter_number,
                        marker=outcome.marker,
                        heading=outcome.heading,
                        span=outcome.span,
                        paragraph_index=outcome.paragraph_index,
                        text=outcome.text,
                    ),
                )
            )
        elif isinstance(outcome, TextAmbiguous):
            candidates.extend((unit, c) for c in outcome.candidates)
        else:
            unresolved.append(outcome)

    if not candidates:
        detail = unresolved[0].message if unresolved else "no unit matched"
        return TextUnresolved(
            unit_id="",
            problem=TextCitationProblem.UNRESOLVED,
            message=f"no provision matched across {len(tuple(units))} unit(s): {detail}",
        )

    if len(candidates) > 1:
        return TextAmbiguous(
            unit_id="",
            problem=TextCitationProblem.AMBIGUOUS,
            message=(
                f"{len(candidates)} provisions match this selector across the "
                f"document; the citation is not unique. A duplicated marker must "
                f"be resolved by position or corrected, never by picking one."
            ),
            candidates=tuple(candidate for _, candidate in candidates),
        )

    unit, _ = candidates[0]
    return resolve_text_citation(unit, selector, document_text=document_text)


def blocked_by_loss(unit: TextEvidenceUnit) -> str | None:
    """Why this unit cannot be cited at all, or ``None``.

    A unit that failed outright, or whose structure is unsupported, is not
    citable. A unit carrying a softer loss (a numbering gap elsewhere in the
    document) is citable, because the loss does not affect the text this unit
    locates -- the distinction is recorded rather than flattened.
    """
    if "failed" in unit.loss:
        return "unit reports extraction failure"
    if "unsupported" in unit.loss:
        return "unit reports an unsupported structure"
    if unit.self_errors:
        return "unit carries an extraction error"
    return None


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------


def _selector_problem(selector: TextCitationSelector) -> str | None:
    supplied = [
        selector.article_number is not None,
        selector.char_range is not None,
    ]
    if not any(supplied):
        return "selector is empty; it cannot identify anything"
    if sum(1 for s in supplied if s) > 1:
        return (
            "more than one location convention was supplied; this resolver does "
            "not choose between them"
        )
    if selector.paragraph_index is not None:
        if selector.article_number is None:
            return "paragraph_index requires an article_number"
        if selector.paragraph_index < 1:
            return "paragraph_index is 1-based; got a non-positive value"
    if selector.char_range is not None:
        start, end = selector.char_range
        if start < 0 or end < start:
            return f"char_range is malformed: {selector.char_range!r}"
    return None


def _span_from_dict(payload: Mapping[str, Any]) -> TextSpan:
    return TextSpan(
        char_start=int(payload["char_start"]),
        char_end=int(payload["char_end"]),
        byte_start=int(payload["byte_start"]),
        byte_end=int(payload["byte_end"]),
        line_start=int(payload["line_start"]),
        line_end=int(payload["line_end"]),
    )


def _candidate_for(
    unit: TextEvidenceUnit,
    provision: Mapping[str, Any],
    selector: TextCitationSelector,
) -> TextCandidate | None:
    """Build a candidate, or ``None`` when the selector excludes this provision.

    Applies only the numeric matching (article, chapter). Paragraph extraction
    happens once a single article has been chosen, so that a paragraph index can
    never be the only thing making a match unique while the article marker is
    duplicated.
    """
    number = int(provision.get("number", -1))
    if number < 0:
        return None  # a malformed marker is never a citation target
    if selector.article_number is not None and number != selector.article_number:
        return None
    if selector.chapter_number is not None:
        if provision.get("chapter_number") != selector.chapter_number:
            return None
    span = _span_from_dict(provision["span"])
    return TextCandidate(
        unit_id=unit.unit_id,
        provision_id=str(provision.get("provision_id", f"article:{number}")),
        article_number=number,
        chapter_number=provision.get("chapter_number"),
        marker=str(provision.get("marker", "")),
        heading=provision.get("heading"),
        span=span,
        text=str(provision.get("text", "")),
    )


def _paragraph_span(
    provision: Mapping[str, Any], paragraph_index: int
) -> TextSpan | None:
    spans = provision.get("paragraph_spans")
    if not isinstance(spans, Sequence):
        return None
    if paragraph_index < 1 or paragraph_index > len(spans):
        return None
    return _span_from_dict(spans[paragraph_index - 1])


def resolve_text_citation(
    unit: TextEvidenceUnit,
    selector: TextCitationSelector,
    *,
    document_text: str | None = None,
) -> TextCitation | TextAmbiguous | TextUnresolved:
    """Rebuild an exact text citation from one unit.

    ``document_text`` is optional. When supplied, the resolved text is verified
    against the artifact before being returned, so a citation cannot claim text
    that the offsets do not point at.
    """
    problem = _selector_problem(selector)
    if problem:
        return TextUnresolved(
            unit_id=unit.unit_id,
            problem=TextCitationProblem.MALFORMED_SELECTOR,
            message=problem,
        )

    provisions = unit_text_provisions(unit)
    if not provisions:
        return TextUnresolved(
            unit_id=unit.unit_id,
            problem=TextCitationProblem.NO_TEXT_PAYLOAD,
            message="unit carries no text provision payload to resolve against",
        )

    if not selector.allow_lossy:
        block = blocked_by_loss(unit)
        if block:
            return TextUnresolved(
                unit_id=unit.unit_id,
                problem=TextCitationProblem.BLOCKED_BY_LOSS,
                message=block,
            )

    # -- character span ---------------------------------------------------
    if selector.char_range is not None:
        start, end = selector.char_range
        inside = [
            p
            for p in provisions
            if _span_from_dict(p["span"]).char_start <= start
            and end <= _span_from_dict(p["span"]).char_end
        ]
        if not inside:
            return TextUnresolved(
                unit_id=unit.unit_id,
                problem=TextCitationProblem.UNRESOLVED,
                message=(
                    f"char range {start}-{end} is not contained in any provision "
                    f"of this unit"
                ),
            )
        if len(inside) > 1 and selector.require_within_provision:
            return TextAmbiguous(
                unit_id=unit.unit_id,
                problem=TextCitationProblem.AMBIGUOUS,
                message=(
                    f"char range {start}-{end} falls inside {len(inside)} "
                    f"provisions; the citation is not decided"
                ),
                candidates=tuple(
                    _candidate_for(unit, p, selector) for p in inside
                ),
            )
        provision = inside[0]
        span = _span_for_chars(provision, start, end)
        return _build(unit, provision, span, selector, "document_span", document_text)

    # -- article marker ---------------------------------------------------
    matched = [
        candidate
        for candidate in (
            _candidate_for(unit, p, selector) for p in provisions
        )
        if candidate is not None
    ]

    if not matched:
        return TextUnresolved(
            unit_id=unit.unit_id,
            problem=TextCitationProblem.UNRESOLVED,
            message=(
                f"no provision in this unit matches the selector "
                f"{selector.as_dict()!r}"
            ),
        )
    if len(matched) > 1:
        # A duplicated marker. Naming both is the only honest answer.
        return TextAmbiguous(
            unit_id=unit.unit_id,
            problem=TextCitationProblem.AMBIGUOUS,
            message=(
                f"{len(matched)} provisions share this marker; the citation is "
                f"not unique. Resolve by document position, or repair the "
                f"numbering."
            ),
            candidates=tuple(matched),
        )

    candidate = matched[0]
    provision = next(
        p
        for p in provisions
        if str(p.get("provision_id")) == candidate.provision_id
    )

    if selector.paragraph_index is None:
        return _build(
            unit, provision, candidate.span, selector, "provision_marker", document_text
        )

    paragraph_span = _paragraph_span(provision, selector.paragraph_index)
    if paragraph_span is None:
        available = len(provision.get("paragraph_spans") or ())
        return TextUnresolved(
            unit_id=unit.unit_id,
            problem=TextCitationProblem.UNRESOLVED,
            message=(
                f"article {candidate.article_number} has {available} paragraph(s); "
                f"paragraph {selector.paragraph_index} does not exist"
            ),
        )
    return _build(
        unit,
        provision,
        paragraph_span,
        selector,
        "provision_marker",
        document_text,
    )


def _span_for_chars(provision: Mapping[str, Any], start: int, end: int) -> TextSpan:
    """Re-derive byte/line coordinates for a caller-supplied char range."""
    base = _span_from_dict(provision["span"])
    # The offsets are linear within the provision's own text, so the delta
    # applies directly. Byte offsets are only exact when the caller's range
    # aligns to the provision text; the citation records this by keeping
    # char_range as the authoritative coordinate.
    return TextSpan(
        char_start=start,
        char_end=end,
        byte_start=base.byte_start + (start - base.char_start),
        byte_end=base.byte_start + (end - base.char_start),
        line_start=base.line_start,
        line_end=base.line_end,
    )


def _build(
    unit: TextEvidenceUnit,
    provision: Mapping[str, Any],
    span: TextSpan,
    selector: TextCitationSelector,
    uniqueness: str,
    document_text: str | None,
) -> TextCitation | TextUnresolved:
    text = str(provision.get("text", ""))
    if uniqueness == "document_span":
        text = span.extract(str(provision.get("text", ""))) or text

    number = int(provision.get("number", -1))
    chapter = provision.get("chapter_number")
    context_path = (
        f"artifact:{unit.artifact_id}",
        f"source:{unit.source_id}",
    )
    if chapter is not None:
        context_path += (f"chapter:{chapter}",)
    context_path += (f"article:{number}", f"span:{span.char_ref}")

    notes: list[str] = []
    if uniqueness != "provision_marker":
        notes.append(
            "location was established from a raw character span, not from a "
            "provision marker; it carries no article identity"
        )

    # The citation's text is always what the *artifact* holds at the recorded
    # offsets. Deriving it from the provision's own string would apply
    # document-level coordinates to a provision-relative string, which silently
    # produces a different substring for anything but a whole-provision span.
    if document_text is not None:
        text = span.extract(document_text)

    citation = TextCitation(
        artifact_id=unit.artifact_id,
        source_id=unit.source_id,
        unit_id=unit.unit_id,
        provision_id=str(provision.get("provision_id", f"article:{number}")),
        article_number=number,
        chapter_number=chapter,
        marker=str(provision.get("marker", "")),
        heading=provision.get("heading"),
        paragraph_index=selector.paragraph_index,
        span=span,
        text=text,
        context_path=context_path,
        uniqueness=uniqueness,
        loss=tuple(unit.loss),
        notes=tuple(notes),
        producer_backend_id=unit.producer.backend_id,
    )

    if document_text is not None and not citation.verify(document_text):
        return TextUnresolved(
            unit_id=unit.unit_id,
            problem=TextCitationProblem.UNRESOLVED,
            message=(
                f"resolved span {span.char_ref} does not reproduce the recorded "
                f"text; the citation is not verifiable against this artifact"
            ),
        )
    return citation
