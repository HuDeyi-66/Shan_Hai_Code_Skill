"""ShanHai text reading: exact offsets and legal structure detection.

Stdlib only, deterministic, read-only. This is ShanHai's private support code --
Core knows nothing about articles, chapters or character spans.

WHY OFFSETS ARE COMPUTED EXPLICITLY
-----------------------------------
A text citation is only checkable if it can be re-located in the *artifact*. So
every provision carries three coordinate systems computed from the same buffer:

* **character span** -- Python string indices;
* **byte span**     -- UTF-8 offsets, so the citation survives a different
  decoder;
* **line span**     -- 1-based lines, so a human can check it in an editor.

All three are recorded because a consumer may hold any one of them, and a
citation that cannot be checked is not evidence.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
-----------------------------------------
No retrieval, no ranking, no fuzzy matching, no similarity search. Structure
detection is exact pattern matching on numbered Chinese legal markers
(``第X条`` / ``第X章``). If the markers are not there, that is reported as an
unsupported structure -- not guessed at.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

__all__ = [
    "TextSpan",
    "TextProvision",
    "TextDocument",
    "StructuralCode",
    "STRUCTURAL_CODES",
    "normalize_newlines",
    "line_offsets",
    "classification",
    "read_text_document",
    "read_text_bytes",
]


# --------------------------------------------------------------------------
# structure vocabulary (Skill-side; Core keeps its own generic loss kinds)
# --------------------------------------------------------------------------


class StructuralCode:
    """The six structural conditions this Skill must keep distinct.

    These are ShanHai's own vocabulary. They are deliberately *not* added to
    Core's ``TextLossKind``: Core is sealed and its vocabulary is generic. Each code
    maps onto Core loss kinds, and the precise code is recorded in the unit
    payload and in run diagnostics, so a consumer can recover the distinction
    without Core knowing the word "article".
    """

    #: The artifact contains no text at all.
    EMPTY_ARTIFACT = "empty_artifact"

    #: The text does not look like numbered legal text.
    UNSUPPORTED_STRUCTURE = "unsupported_structure"

    #: An expected marker is absent from the document.
    MISSING_MARKER = "missing_marker"

    #: A marker-shaped line is present but does not parse.
    MALFORMED_MARKER = "malformed_marker"

    #: Numbering skips a value with no marker-shaped text in between.
    NUMBERING_GAP = "numbering_gap"

    #: The same marker occurs more than once.
    DUPLICATE_MARKER = "duplicate_marker"

    #: The file could not be decoded as UTF-8.
    ENCODING_FAILURE = "encoding_failure"

    ALL = (
        EMPTY_ARTIFACT,
        UNSUPPORTED_STRUCTURE,
        MISSING_MARKER,
        MALFORMED_MARKER,
        NUMBERING_GAP,
        DUPLICATE_MARKER,
        ENCODING_FAILURE,
    )


STRUCTURAL_CODES = StructuralCode.ALL

#: Structural code -> Core ``TextLossKind``. Recorded here so the mapping is visible
#: in one place rather than scattered through the Skill.
_STRUCTURAL_TO_LOSS_KIND: dict[str, str] = {
    StructuralCode.EMPTY_ARTIFACT: "empty",
    StructuralCode.UNSUPPORTED_STRUCTURE: "unsupported",
    StructuralCode.MISSING_MARKER: "not_detected",
    StructuralCode.MALFORMED_MARKER: "failed",
    StructuralCode.NUMBERING_GAP: "unknown",
    StructuralCode.DUPLICATE_MARKER: "unknown",
    StructuralCode.ENCODING_FAILURE: "failed",
}


# --------------------------------------------------------------------------
# spans
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TextSpan:
    """One region of the artifact in three coordinate systems at once.

    ``char_start``/``char_end`` are half-open Python string indices.
    ``byte_start``/``byte_end`` are half-open UTF-8 offsets.
    ``line_start``/``line_end`` are 1-based and inclusive.
    """

    char_start: int
    char_end: int
    byte_start: int
    byte_end: int
    line_start: int
    line_end: int

    PROVISIONAL = True

    def __post_init__(self) -> None:
        if self.char_end < self.char_start:
            raise ValueError("char_end must not precede char_start")
        if self.byte_end < self.byte_start:
            raise ValueError("byte_end must not precede byte_start")
        if self.line_end < self.line_start:
            raise ValueError("line_end must not precede line_start")

    @property
    def char_length(self) -> int:
        return self.char_end - self.char_start

    @property
    def byte_length(self) -> int:
        return self.byte_end - self.byte_start

    def extract(self, text: str) -> str:
        """The exact substring this span refers to."""
        return text[self.char_start : self.char_end]

    @property
    def char_ref(self) -> str:
        return f"char:{self.char_start}-{self.char_end}"

    @property
    def byte_ref(self) -> str:
        return f"byte:{self.byte_start}-{self.byte_end}"

    @property
    def line_ref(self) -> str:
        return f"line:{self.line_start}-{self.line_end}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "char_start": self.char_start,
            "char_end": self.char_end,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "char_length": self.char_length,
            "byte_length": self.byte_length,
            "char_ref": self.char_ref,
            "byte_ref": self.byte_ref,
            "line_ref": self.line_ref,
        }


@dataclass
class TextProvision:
    """One detected article (``第X条``) with everything needed to locate it."""

    number: int
    marker: str
    heading: str | None
    text: str
    span: TextSpan
    chapter_number: int | None = None
    chapter_marker: str | None = None
    paragraph_spans: tuple[TextSpan, ...] = ()
    numbers_in_marker_form: tuple[str, ...] = ()
    malformed: bool = False
    malformed_reason: str | None = None
    #: Which structural code explains ``malformed``. Without it a malformed
    #: provisional article could only be mapped to one blanket Core loss kind,
    #: which would report ``failed`` for an article whose real condition is
    #: ``missing_marker`` -- the same conflation the document-level vocabulary is
    #: kept separate to avoid.
    malformed_code: str | None = None

    PROVISIONAL = True

    @property
    def provision_id(self) -> str:
        return f"article:{self.number}"

    @property
    def paragraphs(self) -> int:
        return len(self.paragraph_spans)

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "marker": self.marker,
            "heading": self.heading,
            "chapter_number": self.chapter_number,
            "chapter_marker": self.chapter_marker,
            "span": self.span.as_dict(),
            "paragraph_count": self.paragraphs,
            "paragraph_spans": [s.as_dict() for s in self.paragraph_spans],
            "numbers_in_marker_form": list(self.numbers_in_marker_form),
            "malformed": self.malformed,
            "malformed_reason": self.malformed_reason,
            "malformed_code": self.malformed_code,
            "text_length": len(self.text),
        }


@dataclass
class TextDocument:
    """A text artifact as this Skill observed it."""

    text: str
    spans: tuple[TextSpan, ...] = ()
    title: str | None = None
    chapters: tuple[tuple[int, str, TextSpan], ...] = ()
    provisions: tuple[TextProvision, ...] = ()
    classification: str = "unknown"
    structural_findings: tuple[tuple[str, str], ...] = ()
    loss: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    fatal: bool = False
    backend_id: str = "unknown"
    backend_version: str = "unknown"
    backend_path: str = "unknown"
    char_count: int = 0
    byte_count: int = 0
    line_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    PROVISIONAL = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "classification": self.classification,
            "char_count": self.char_count,
            "byte_count": self.byte_count,
            "line_count": self.line_count,
            "span_count": len(self.spans),
            "chapter_count": len(self.chapters),
            "provision_count": len(self.provisions),
            "provision_numbers": [p.number for p in self.provisions],
            "structural_findings": [
                {"code": code, "detail": detail}
                for code, detail in self.structural_findings
            ],
            "loss": list(self.loss),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "backend_id": self.backend_id,
            "metadata": self.metadata,
        }


# --------------------------------------------------------------------------
# marker patterns
# --------------------------------------------------------------------------

#: Chinese legal article marker: ``第二条``, ``第 2 条``, ``第十二条``.
_ARTICLE_MARKER = re.compile(r"^\s*(第\s*([0-9]+|[〇零一二三四五六七八九十百千]+)\s*条)")

#: Chinese legal chapter marker: ``第一章``.
_CHAPTER_MARKER = re.compile(r"^\s*(第\s*([0-9]+|[〇零一二三四五六七八九十百千]+)\s*章)")

#: Something that plainly *tries* to be an article marker but does not parse:
#: ``第2``, ``第条``, or a bare number line like ``2.``.
_MALFORMED_ARTICLE = re.compile(r"^\s*(第\s*条|第\s*[0-9〇零一二三四五六七八九十百千]+\s*$|[0-9]+\s*[.、]\s*\S)")

#: An article marker whose numeral uses a form this reader does not support, such
#: as ``第廿条`` (twenty) or ``第百条``. The *shape* is unambiguously an article
#: marker -- it ends in ``条`` -- but the numeral cannot be resolved.
#:
#: This is what makes ``missing_marker`` a real state rather than dead
#: vocabulary: it is distinct from ``malformed_marker`` (which is not a
#: well-formed marker at all) and from ``numbering_gap`` (where the expected
#: position holds nothing marker-shaped). Silently treating it as a plain gap
#: would conflate "the article is absent" with "the reader cannot read the
#: article's number".
_UNSUPPORTED_NUMERAL_ARTICLE = re.compile(
    r"^\s*第\s*([0-9A-Za-z〇零一二三四五六七八九十百千廿卅两]+)\s*条"
)

#: A numbered Latin heading, which a legal-text Skill is not built to read.
_LATIN_NUMBERED_HEADING = re.compile(r"^\s*(Article|Section|Clause)\s+[0-9IVXivx]+")

_CJK_DIGITS = {
    "〇": 0, "零": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}


def _cjk_number_to_int(text: str) -> int | None:
    """Parse ``十二``/``二十三``-style numerals. ``None`` when not parseable.

    Handles the forms that occur in Chinese legal markers: units of ``十`` and
    ``百``, with or without a leading digit.
    """
    cleaned = text.strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)
    try:
        total = 0
        section = 0
        for char in cleaned:
            if char in _CJK_DIGITS:
                section = _CJK_DIGITS[char]
            elif char == "十":
                section = 1 if section == 0 else section
                total += section * 10
                section = 0
            elif char == "百":
                section = 1 if section == 0 else section
                total += section * 100
                section = 0
            else:
                return None
        return total + section
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


def normalize_newlines(text: str) -> str:
    """Normalize CRLF/CR to LF.

    Recorded as a normalization, not applied silently: the byte offsets in the
    resulting spans refer to the *artifact* bytes, which the reader computes
    separately, so nothing is lost by normalizing in memory.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def line_offsets(text: str) -> tuple[list[int], list[int]]:
    """Return ``(char_line_starts, char_line_ends)`` for every line.

    ``char_line_ends[i]`` excludes the newline. Empty text yields one empty line,
    which keeps line numbering total rather than special-cased.
    """
    starts: list[int] = [0]
    ends: list[int] = []
    for index, char in enumerate(text):
        if char == "\n":
            ends.append(index)
            starts.append(index + 1)
    ends.append(len(text))
    return starts, ends


def classification(text: str) -> str:
    """Coarse guess at whether this is numbered legal text.

    Deliberately coarse and deliberately not a similarity score: it answers
    "does the shape exist?", so that a document without it is reported as an
    unsupported structure rather than parsed into nonsense.
    """
    if not text.strip():
        return "empty"
    if any(_ARTICLE_MARKER.match(line) for line in text.split("\n")):
        return "legal_numbered"
    if any(_LATIN_NUMBERED_HEADING.match(line) for line in text.split("\n")):
        return "legal_latin"
    return "unsupported"


# --------------------------------------------------------------------------
# structure extraction
# --------------------------------------------------------------------------


def _byte_offset(text: str, char_index: int) -> int:
    """UTF-8 byte offset of a character index. O(n) per call, called O(units)."""
    return len(text[:char_index].encode("utf-8"))


def _span_for(
    text: str,
    char_start: int,
    char_end: int,
    line_starts: Sequence[int],
    line_ends: Sequence[int],
) -> TextSpan:
    start_line = _line_of(char_start, line_starts)
    end_char = char_end - 1 if char_end > char_start else char_start
    end_line = _line_of(min(end_char, max(len(text) - 1, 0)), line_starts)
    return TextSpan(
        char_start=char_start,
        char_end=char_end,
        byte_start=_byte_offset(text, char_start),
        byte_end=_byte_offset(text, char_end),
        line_start=start_line,
        line_end=end_line,
    )


def _line_of(char_index: int, line_starts: Sequence[int]) -> int:
    """1-based line number containing ``char_index``."""
    low, high = 0, len(line_starts) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if line_starts[mid] <= char_index:
            low = mid
        else:
            high = mid - 1
    return low + 1


def _iter_lines(text: str, line_starts: Sequence[int]) -> Iterator[tuple[int, str]]:
    """Yield ``(char_offset_of_line_start, line_text_without_newline)``."""
    for index, start in enumerate(line_starts):
        end = text.find("\n", start)
        if end == -1:
            end = len(text)
        yield start, text[start:end]


def read_text_document(
    text: str,
    *,
    backend_id: str = "unknown",
    backend_version: str = "unknown",
    backend_path: str = "unknown",
    byte_count: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> TextDocument:
    """Detect numbered legal structure in ``text``.

    Every finding is reported. Nothing is repaired, nothing is guessed at, and a
    document with no recognizable structure produces no provisions plus an
    explicit ``unsupported_structure`` finding.
    """
    metadata = dict(metadata or {})
    original = text
    text = normalize_newlines(text)
    if text != original:
        metadata["newline_normalized"] = True

    char_count = len(text)
    byte_count = (
        byte_count if byte_count is not None else len(text.encode("utf-8"))
    )
    line_starts, line_ends = line_offsets(text)
    line_count = len(line_starts)

    base = TextDocument(
        text=text,
        backend_id=backend_id,
        backend_version=backend_version,
        backend_path=backend_path,
        char_count=char_count,
        byte_count=byte_count,
        line_count=line_count,
        metadata=metadata,
    )

    findings: list[tuple[str, str]] = []
    warnings: list[str] = []

    if not text.strip():
        findings.append(
            (StructuralCode.EMPTY_ARTIFACT, "artifact contains no non-whitespace text")
        )
        base.classification = "empty"
        base.structural_findings = tuple(findings)
        base.loss = (_STRUCTURAL_TO_LOSS_KIND[StructuralCode.EMPTY_ARTIFACT],)
        return base

    document_classification = classification(text)
    base.classification = document_classification
    if document_classification == "unsupported":
        detail = (
            "no numbered legal marker (第X条) found; the first non-empty line is "
            f"{_first_non_empty(text)!r}"
        )
        findings.append((StructuralCode.UNSUPPORTED_STRUCTURE, detail))
        base.structural_findings = tuple(findings)
        base.loss = (_STRUCTURAL_TO_LOSS_KIND[StructuralCode.UNSUPPORTED_STRUCTURE],)
        return base
    if document_classification == "legal_latin":
        detail = "numbered Latin headings (Article N) are outside this Skill's scope"
        findings.append((StructuralCode.UNSUPPORTED_STRUCTURE, detail))
        base.structural_findings = tuple(findings)
        base.loss = (_STRUCTURAL_TO_LOSS_KIND[StructuralCode.UNSUPPORTED_STRUCTURE],)
        return base

    # -- walk the lines, tracking chapters and articles -------------------
    chapters: list[tuple[int, str, TextSpan]] = []
    provisions: list[TextProvision] = []
    current_chapter: int | None = None
    current_chapter_marker: str | None = None
    open_article: TextProvision | None = None
    open_start: int | None = None
    open_lines: list[tuple[int, str]] = []
    marker_numbers: list[int] = []
    malformed_lines: list[tuple[int, int, str]] = []
    #: Markers whose shape is a well-formed article marker but whose numeral this
    #: reader cannot resolve: ``(start, end, line, numeral)``.
    unparsed_markers: list[tuple[int, int, str, str]] = []
    title: str | None = None
    seen_preamble_lines = 0

    def close_article(end_offset: int) -> None:
        nonlocal open_article, open_start, open_lines
        if open_article is None or open_start is None:
            return
        body = text[open_start:end_offset]
        # The span must describe exactly the text that is recorded, so trailing
        # newlines are excluded from both at once. Computing the span from
        # ``end_offset`` after stripping the body would leave the span covering
        # characters the recorded text does not contain, and a citation built
        # from that span would not verify against the artifact.
        trimmed = body.rstrip("\n")
        span_end = open_start + len(trimmed)
        body = trimmed
        paragraphs, heading = _split_article(body, open_start, text, line_starts, line_ends)
        open_article.text = body
        open_article.heading = heading
        open_article.paragraph_spans = paragraphs
        open_article.span = _span_for(text, open_start, span_end, line_starts, line_ends)
        provisions.append(open_article)
        open_article = None
        open_start = None
        open_lines = []

    for offset, raw_line in _iter_lines(text, line_starts):
        stripped = raw_line.strip()

        chapter_match = _CHAPTER_MARKER.match(raw_line)
        if chapter_match:
            close_article(offset)
            number = _cjk_number_to_int(chapter_match.group(2))
            marker = chapter_match.group(1).strip()
            if number is None:
                findings.append(
                    (
                        StructuralCode.MALFORMED_MARKER,
                        f"chapter marker does not parse: {marker!r}",
                    )
                )
            else:
                current_chapter = number
                current_chapter_marker = marker
                chapters.append((number, marker, _span_for(text, offset, offset + len(raw_line), line_starts, line_ends)))
            continue

        article_match = _ARTICLE_MARKER.match(raw_line)
        if article_match:
            close_article(offset)
            raw_number = article_match.group(2)
            number = _cjk_number_to_int(raw_number)
            marker = article_match.group(1).strip()
            if number is None:
                # The marker *shape* is well formed (``第...条``) but the numeral
                # cannot be resolved. Recorded as an unparsed marker, and the
                # line is kept as a malformed article so the text is not
                # silently dropped.
                unparsed_markers.append(
                    (offset, offset + len(raw_line), marker, raw_number)
                )
                findings.append(
                    (
                        StructuralCode.MISSING_MARKER,
                        f"article marker present but its numeral is not "
                        f"resolvable: {marker!r}",
                    )
                )
                open_article = TextProvision(
                    number=-1,
                    marker=marker,
                    heading=None,
                    text="",
                    span=_span_for(text, offset, offset + len(raw_line), line_starts, line_ends),
                    chapter_number=current_chapter,
                    chapter_marker=current_chapter_marker,
                    malformed=True,
                    malformed_reason="numeral is not resolvable",
                    malformed_code=StructuralCode.MISSING_MARKER,
                )
                open_start = offset
                continue
            marker_numbers.append(number)
            # The text between the marker and the first newline is the heading.
            marker_end = offset + article_match.end()
            remainder = text[marker_end : text.find("\n", offset) if text.find("\n", offset) != -1 else len(text)]
            open_article = TextProvision(
                number=number,
                marker=marker,
                heading=remainder.strip() or None,
                text="",
                span=_span_for(text, offset, offset + len(raw_line), line_starts, line_ends),
                chapter_number=current_chapter,
                chapter_marker=current_chapter_marker,
                numbers_in_marker_form=(raw_number,),
            )
            open_start = offset
            continue

        # An article marker whose numeral form this reader does not support, e.g.
        # ``第廿条``. Captured before the generic malformed check so the state is
        # reported as a *missing* marker rather than a broken one: the marker is
        # well formed, the reader simply cannot resolve it.
        unsupported_match = _UNSUPPORTED_NUMERAL_ARTICLE.match(raw_line)
        if unsupported_match:
            close_article(offset)
            numeral = unsupported_match.group(1)
            marker = unsupported_match.group(0).strip()
            unparsed_markers.append(
                (offset, offset + len(raw_line), marker, numeral)
            )
            findings.append(
                (
                    StructuralCode.MISSING_MARKER,
                    f"article marker uses an unsupported numeral form "
                    f"{numeral!r} in {raw_line.strip()!r}",
                )
            )
            # The line is kept as a provisional article rather than skipped. It is
            # a real article whose number this reader cannot read, so its text
            # must still be reachable: dropping the line here would make an entire
            # article vanish from the evidence with only a structural code to show
            # for it -- content omission disguised as a diagnostic.
            open_article = TextProvision(
                number=-1,
                marker=marker,
                heading=None,
                text="",
                span=_span_for(text, offset, offset + len(raw_line), line_starts, line_ends),
                chapter_number=current_chapter,
                chapter_marker=current_chapter_marker,
                malformed=True,
                malformed_reason="numeral form is not supported",
                malformed_code=StructuralCode.MISSING_MARKER,
            )
            open_start = offset
            continue

        # Not a marker. Could it be a broken marker, or a document title?
        if _MALFORMED_ARTICLE.match(raw_line):
            # A marker-shaped line ends the previous article: it is a failed
            # separator, not body text. Failing to close here would let the
            # previous article's span absorb the malformed line, which both
            # mis-states that article's extent and hides this entry from the
            # gap-versus-malformed analysis further down.
            close_article(offset)
            malformed_lines.append((offset, offset + len(raw_line), raw_line.strip()))
            findings.append(
                (
                    StructuralCode.MALFORMED_MARKER,
                    f"marker-shaped line does not parse: {raw_line.strip()!r}",
                )
            )
            # Kept as an explicitly *unclassified* provisional fragment rather
            # than skipped. The reader cannot assert an article number here, but
            # it can assert that this region of the artifact exists, and text that
            # appears in no unit at all is indistinguishable from text that was
            # never in the artifact. The fragment carries loss, is never a
            # citation target (its number is below 1), and keeps the artifact's
            # structural lines fully represented in the evidence.
            open_article = TextProvision(
                number=-1,
                marker=raw_line.strip(),
                heading=None,
                text="",
                span=_span_for(
                    text, offset, offset + len(raw_line), line_starts, line_ends
                ),
                chapter_number=current_chapter,
                chapter_marker=current_chapter_marker,
                malformed=True,
                malformed_reason="marker-shaped line does not parse",
                malformed_code=StructuralCode.MALFORMED_MARKER,
            )
            open_start = offset
            continue

        if open_article is None and stripped:
            # Before the first article: treat a short heading-like line as the
            # document title, anything else as preamble.
            seen_preamble_lines += 1
            if title is None and len(stripped) <= 40 and seen_preamble_lines == 1:
                title = stripped

    close_article(len(text))

    # -- structural findings from the numbering sequence ------------------
    numbers = sorted({n for n in marker_numbers if n > 0})
    duplicates = sorted({n for n in marker_numbers if marker_numbers.count(n) > 1})

    malformed_in_ranges: list[tuple[int, int]] = [
        (start, end) for start, end, _ in malformed_lines
    ]
    unparsed_in_ranges: list[tuple[int, int, str]] = [
        (start, end, numeral) for start, end, _, numeral in unparsed_markers
    ]

    for left, right in zip(numbers, numbers[1:]):
        if right - left <= 1:
            continue
        left_span = next((p for p in provisions if p.number == left), None)
        right_span = next((p for p in provisions if p.number == right), None)
        start_char = left_span.span.char_end if left_span else 0
        end_char = right_span.span.char_start if right_span else char_count
        gap_values = list(range(left + 1, right))

        # Three distinct conditions live in a numbering gap, and they must not be
        # conflated:
        #
        #   missing_marker  a well-formed article marker whose numeral this reader
        #                   cannot resolve (e.g. 第廿条) sits in the gap;
        #   malformed_marker a marker-shaped line that is not a well-formed marker
        #                   sits in the gap;
        #   numbering_gap   nothing marker-shaped is there at all.
        #
        # Reporting an unreadable marker as a plain gap would claim the article is
        # absent when in fact the reader could not read its number.
        unparsed_here = [
            numeral
            for start, end, numeral in unparsed_in_ranges
            if start_char <= start < end_char
        ]
        if unparsed_here:
            findings.append(
                (
                    StructuralCode.MISSING_MARKER,
                    f"article number(s) {gap_values} between {left} and {right} "
                    f"carry an article marker this reader cannot resolve "
                    f"(numeral form(s) {unparsed_here}); reported as a marker the "
                    f"reader does not support, not as an absent article",
                )
            )
            continue

        suspicious = any(start_char <= s < end_char for s, _ in malformed_in_ranges)
        if suspicious:
            findings.append(
                (
                    StructuralCode.MALFORMED_MARKER,
                    f"missing article number(s) {gap_values} between {left} and "
                    f"{right} coincide with marker-shaped text that does not "
                    f"parse; reported as malformed marker, not as absent",
                )
            )
            continue

        for value in gap_values:
            findings.append(
                (
                    StructuralCode.NUMBERING_GAP,
                    f"article {value} is missing between {left} and {right}",
                )
            )

    for value in duplicates:
        occurrences = [p.number for p in provisions if p.number == value]
        findings.append(
            (
                StructuralCode.DUPLICATE_MARKER,
                f"article marker {value} occurs {len(occurrences)} times",
            )
        )
        warnings.append(
            f"duplicate article marker {value}: citations to it cannot be unique"
        )

    losses: list[str] = []
    for code, _ in findings:
        kind = _STRUCTURAL_TO_LOSS_KIND.get(code)
        if kind and kind not in losses:
            losses.append(kind)

    base.spans = tuple(p.span for p in provisions) + tuple(
        span for _, _, span in chapters
    )
    base.title = title
    base.chapters = tuple(chapters)
    base.provisions = tuple(provisions)
    # One entry per condition. The gap analysis deliberately corroborates a
    # malformed marker it already saw, and that corroboration must not appear as
    # a second finding for the same text.
    deduped: list[tuple[str, str]] = []
    seen_codes: set[str] = set()
    for code, detail in findings:
        if code in seen_codes:
            continue
        seen_codes.add(code)
        deduped.append((code, detail))
    base.structural_findings = tuple(deduped)
    base.loss = tuple(losses)
    base.warnings = tuple(warnings)
    return base


def _first_non_empty(text: str) -> str:
    for line in text.split("\n"):
        if line.strip():
            return line.strip()[:60]
    return ""


def _split_article(
    body: str,
    body_start: int,
    full_text: str,
    line_starts: Sequence[int],
    line_ends: Sequence[int],
) -> tuple[tuple[TextSpan, ...], str | None]:
    """Split an article body into paragraph spans on blank lines.

    The heading (text on the marker line after ``第X条``) is not a paragraph.
    Paragraphs are the blank-line-separated blocks after it.
    """
    if not body:
        return (), None
    first_newline = body.find("\n")
    if first_newline == -1:
        return (), None
    heading = body[:first_newline].strip() or None
    rest_start = body_start + first_newline + 1

    spans: list[TextSpan] = []
    cursor = rest_start
    block_start: int | None = None
    for offset, raw_line in _iter_lines(full_text, line_starts):
        if offset < rest_start:
            continue
        if offset >= body_start + len(body):
            break
        if raw_line.strip():
            if block_start is None:
                block_start = offset
        else:
            if block_start is not None:
                end = offset
                spans.append(_span_for(full_text, block_start, end, line_starts, line_ends))
                block_start = None
        cursor = offset
    if block_start is not None:
        end = body_start + len(body)
        spans.append(_span_for(full_text, block_start, end, line_starts, line_ends))
    return tuple(spans), heading


# --------------------------------------------------------------------------
# byte-level entry point
# --------------------------------------------------------------------------


def read_text_bytes(
    raw: bytes,
    *,
    backend_id: str = "unknown",
    backend_version: str = "unknown",
    backend_path: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> TextDocument:
    """Decode and read an artifact's bytes.

    A UTF-8 decode failure is reported as ``encoding_failure`` and produces no
    provisions. It is never repaired with a lossy fallback decoder, because a
    lossy decode would silently change the text a citation points at.
    """
    try:
        text = unicodedata.normalize("NFC", raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        document = TextDocument(
            text="",
            classification="unknown",
            structural_findings=(
                (
                    StructuralCode.ENCODING_FAILURE,
                    f"artifact is not valid UTF-8: {exc}",
                ),
            ),
            loss=(_STRUCTURAL_TO_LOSS_KIND[StructuralCode.ENCODING_FAILURE],),
            errors=(f"encoding_failure: {exc}",),
            fatal=True,
            backend_id=backend_id,
            backend_version=backend_version,
            backend_path=backend_path,
            byte_count=len(raw),
            metadata=dict(metadata or {}),
        )
        return document
    document = read_text_document(
        text,
        backend_id=backend_id,
        backend_version=backend_version,
        backend_path=backend_path,
        byte_count=len(raw),
        metadata=metadata,
    )
    return document


def structural_loss_kind(code: str) -> str | None:
    """The Core ``TextLossKind`` a structural code maps to, for tests and callers."""
    return _STRUCTURAL_TO_LOSS_KIND.get(code)


def loss_kinds_for(codes: Sequence[str]) -> tuple[str, ...]:
    """Map structural codes to deduplicated Core loss kinds, order preserved."""
    out: list[str] = []
    for code in codes:
        kind = _STRUCTURAL_TO_LOSS_KIND.get(code)
        if kind and kind not in out:
            out.append(kind)
    return tuple(out)
