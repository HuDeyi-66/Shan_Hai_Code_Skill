"""ShanHai text backends.

Same shape as LuoHai's backends, deliberately: a narrow observation contract that
the Skill drives, with explicit injection. No scanning, no auto-discovery, no
registry, no plugin loading.

There is no third-party text backend here. Unlike the workbook case, the Python
standard library decodes UTF-8 honestly, and adding a parser dependency would
mean giving up the exact-offset guarantee that makes a text citation checkable.
The OSS question that mattered for XLSX does not arise.

That is a scope decision, not an oversight: if a future requirement needs a
richer text format, it brings its own backend behind this same contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

from .contracts import TextCapability, TextSupport

from .textio import StructuralCode, TextDocument, read_text_bytes

__all__ = [
    "TEXT_MEDIA_TYPES",
    "TextBackend",
    "FixtureTextBackend",
    "FakeTextBackend",
]

#: Media types this Skill claims. Anything else is warned about and refused.
TEXT_MEDIA_TYPES = (
    "text/plain",
    "text/x-legal",
    "application/text",
)

#: A text backend reads UTF-8 bytes and reports legal structure. Read-only.
_TEXT_CAPABILITIES = (
    TextCapability(
        name="utf8_text_read",
        support=TextSupport.SUPPORTED,
        detail="UTF-8 decoding with exact character, byte and line offsets",
    ),
    TextCapability(
        name="encoding_detection",
        support=TextSupport.UNSUPPORTED,
        detail="only UTF-8 is decoded; a BOM-less legacy encoding is reported as "
               "an encoding failure rather than guessed at",
    ),
    TextCapability(
        name="article_marker_detection",
        support=TextSupport.SUPPORTED,
        detail="numbered Chinese legal markers: 第X条 (article) and 第X章 (chapter), "
               "including 〇零一二三四五六七八九十百 numerals",
    ),
    TextCapability(
        name="latin_numbered_headings",
        support=TextSupport.UNSUPPORTED,
        detail="'Article N' style headings are outside this Skill's scope and are "
               "reported as an unsupported structure",
    ),
    TextCapability(
        name="paragraph_split",
        support=TextSupport.PARTIAL,
        detail="paragraphs are split on blank lines within an article; a "
               "single-paragraph article reflowed without blank lines is one "
               "paragraph",
    ),
    TextCapability(
        name="exact_span_location",
        support=TextSupport.SUPPORTED,
        detail="character, byte and line spans computed from the artifact bytes",
    ),
    TextCapability(
        name="scanned_or_image_text",
        support=TextSupport.UNSUPPORTED,
        detail="no OCR; an image or PDF artifact is not text and is refused",
    ),
    TextCapability(
        name="retrieval_or_ranking",
        support=TextSupport.UNSUPPORTED,
        detail="no retrieval, ranking, similarity or fuzzy matching exists in this "
               "Skill by design",
    ),
)


@runtime_checkable
class TextBackend(Protocol):
    """What the ShanHai Skill needs from any text reader.

    Implementations must be read-only with respect to ``path``.
    """

    backend_id: str
    backend_version: str
    backend_path: str

    def is_available(self) -> bool:
        ...

    def capabilities(self) -> tuple[TextCapability, ...]:
        ...

    def load(self, path: str, options: Mapping[str, Any] | None = None) -> TextDocument:
        ...


@dataclass
class FixtureTextBackend:
    """Deterministic stdlib reader for local UTF-8 text fixtures.

    Reads bytes, hands them to :func:`~skills.shanhai.textio.read_text_bytes`,
    and reports exactly what was and was not found.
    """

    backend_id: str = "fixture.utf8-text"
    backend_version: str = "0.1.0-provisional"
    backend_path: str = "fixture"

    PROVISIONAL = True

    def is_available(self) -> bool:
        return True

    def capabilities(self) -> tuple[TextCapability, ...]:
        return _TEXT_CAPABILITIES

    def load(self, path: str, options: Mapping[str, Any] | None = None) -> TextDocument:
        options = dict(options or {})
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            return TextDocument(
                text="",
                classification="unknown",
                structural_findings=(
                    (StructuralCode.ENCODING_FAILURE, f"artifact is unreadable: {exc}"),
                ),
                loss=("failed",),
                errors=(f"read_failure: {exc}",),
                fatal=True,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                backend_path=self.backend_path,
            )
        document = read_text_bytes(
            raw,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            backend_path=self.backend_path,
            metadata={"encoding": "utf-8", "path": str(path)},
        )
        return document


@dataclass
class FakeTextBackend:
    """In-memory backend with no filesystem dependency.

    Proves the Skill's interface before any file exists, and lets a test drive a
    structural case that is awkward to express as a file (an unparseable marker,
    a marker-shaped line, a byte sequence that is not UTF-8).
    """

    text: str = ""
    raw_bytes: bytes | None = None
    backend_id: str = "fake.text"
    backend_version: str = "provisional"
    backend_path: str = "in-memory"
    available: bool = True
    load_calls: int = 0

    PROVISIONAL = True

    def is_available(self) -> bool:
        return self.available

    def capabilities(self) -> tuple[TextCapability, ...]:
        return _TEXT_CAPABILITIES

    def load(self, path: str, options: Mapping[str, Any] | None = None) -> TextDocument:
        self.load_calls += 1
        raw = (
            self.raw_bytes
            if self.raw_bytes is not None
            else self.text.encode("utf-8")
        )
        return read_text_bytes(
            raw,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            backend_path=self.backend_path,
            metadata={"encoding": "utf-8", "in_memory": True},
        )
