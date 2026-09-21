"""ShanHai -- the second independent SeaFlow Skill.

``ShanHai.LegalTextEvidence`` extracts provision-level evidence from a registered
UTF-8 legal text artifact.

Independent of LuoHai by construction: nothing in this package imports
``skills.luohai``, and nothing in ``skills.luohai`` imports this package. The two
Skills share only the sealed Core. That isolation is asserted by test rather than
left to discipline.

Package layout
--------------
::

    skills/shanhai/
      legal_text_extraction.py   the Skill (ShanHai.LegalTextEvidence)
      backends.py       text observation backends (fixture / fake)
      textio.py         stdlib text reader: exact offsets + structure detection
      citation.py       text citation reconstruction
"""

from .backends import FixtureTextBackend, FakeTextBackend, TextBackend
from .citation import (
    TextAmbiguous,
    TextCandidate,
    TextCitation,
    TextCitationProblem,
    TextCitationSelector,
    TextUnresolved,
    iter_provisions,
    resolve_text_citation,
    resolve_text_citation_across,
    unit_text_context,
    unit_text_provisions,
)
from .legal_text_extraction import (
    DEFAULT_OPTIONS,
    SHANHAI_METADATA_KEY,
    ShanHaiLegalTextEvidence,
)
from .textio import (
    STRUCTURAL_CODES,
    StructuralCode,
    TextDocument,
    TextProvision,
    TextSpan,
    loss_kinds_for,
    read_text_bytes,
    read_text_document,
    structural_loss_kind,
)

__all__ = [
    # the Skill
    "ShanHaiLegalTextEvidence",
    "DEFAULT_OPTIONS",
    "SHANHAI_METADATA_KEY",
    # backends
    "TextBackend",
    "FixtureTextBackend",
    "FakeTextBackend",
    # text model
    "TextSpan",
    "TextProvision",
    "TextDocument",
    "StructuralCode",
    "STRUCTURAL_CODES",
    "read_text_document",
    "read_text_bytes",
    "structural_loss_kind",
    "loss_kinds_for",
    # citation
    "TextCitationSelector",
    "TextCitation",
    "TextCitationProblem",
    "TextUnresolved",
    "TextAmbiguous",
    "TextCandidate",
    "resolve_text_citation",
    "resolve_text_citation_across",
    "unit_text_context",
    "unit_text_provisions",
    "iter_provisions",
]
