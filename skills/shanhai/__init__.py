"""ShanHai -- the official SeaFlow Skill for legal-text evidence.

ShanHai is an **independent open-source component**. It reads UTF-8 legal text,
detects legal structure, emits evidence units with exact character, byte and line
spans, reconstructs citations that can be re-checked against the artifact, and
reports ambiguity or unsupported structure instead of guessing.

Standalone use needs nothing but this package::

    from skills.shanhai import run_legal_text_evidence

    result = run_legal_text_evidence("statute.txt", source_id="statute")

It does not import a private runtime, and it carries its own contract in
``skills/shanhai/contracts.py``.

LuoHai, the sibling tabular Skill, is likewise independent: nothing in this
package imports ``skills.luohai``, and nothing in ``skills.luohai`` imports this
package. That isolation is asserted by test rather than left to discipline.

When a SeaFlow runtime is present it may integrate this Skill as an official
plugin. That integration is implemented **on the runtime's side** -- ShanHai
exposes this API and the runtime adapts it -- so the dependency never points from
this public package into private code.

Package layout
--------------
::

    skills/shanhai/
      api.py             run_legal_text_evidence -- the standalone entry point
      contracts.py       this Skill's own evidence contract
      legal_text_extraction.py   the Skill implementation
      backends.py        text observation backends (fixture / fake)
      textio.py          stdlib text reader: exact offsets + structure detection
      citation.py        text citation reconstruction
"""

from .api import evidence_skill, legal_text_artifact, run_legal_text_evidence
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
from .contracts import (
    TextArtifact,
    TextCapability,
    TextCitationAddress,
    TextContractError,
    TextEvidenceSkill,
    TextEvidenceUnit,
    TextLossKind,
    TextProducer,
    TextRunDiagnostics,
    TextRunError,
    TextRunResult,
    TextRunWarning,
    TextSupport,
    TextUnitClass,
    detect_text_media_type,
    find_text_units,
    text_digest_bytes,
    text_digest_path,
    text_summarise_loss,
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
    # the standalone entry point
    "run_legal_text_evidence",
    "legal_text_artifact",
    "evidence_skill",
    # the Skill implementation and its options
    "ShanHaiLegalTextEvidence",
    "DEFAULT_OPTIONS",
    "SHANHAI_METADATA_KEY",
    # this Skill's own contract
    "TextEvidenceSkill",
    "TextRunResult",
    "TextEvidenceUnit",
    "TextArtifact",
    "TextCitationAddress",
    "TextProducer",
    "TextLossKind",
    "TextUnitClass",
    "TextCapability",
    "TextSupport",
    "TextRunDiagnostics",
    "TextRunWarning",
    "TextRunError",
    "TextContractError",
    "find_text_units",
    "text_summarise_loss",
    "text_digest_bytes",
    "text_digest_path",
    "detect_text_media_type",
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
