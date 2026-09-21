"""The standalone ShanHai entry point.

One function, no framework. It takes the text you have — a path, raw bytes, or
an artifact you built yourself — and returns legal-text evidence with exact
locations, explicit loss and native citations.

ShanHai is an independent open-source component. This module is the whole of its
required surface: nothing here needs a runtime, a service, a registry or a
network, and nothing here imports a private implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .backends import FixtureTextBackend, TextBackend
from .contracts import TextArtifact, TextEvidenceSkill, TextRunResult

__all__ = ["run_legal_text_evidence", "evidence_skill", "legal_text_artifact"]


def evidence_skill(reader: TextBackend | None = None) -> TextEvidenceSkill:
    """Construct the ShanHai Skill, with the deterministic reader by default."""
    from .legal_text_extraction import ShanHaiLegalTextEvidence

    return ShanHaiLegalTextEvidence(reader or FixtureTextBackend())


def legal_text_artifact(
    source: str | Path | bytes | TextArtifact,
    *,
    artifact_id: str | None = None,
    media_type: str | None = None,
) -> TextArtifact:
    """Coerce ``source`` into a re-verifiable text artifact.

    A path is read and digested; bytes are digested as given; an artifact you
    built yourself is passed through untouched, because re-deriving its identity
    would discard the record you made.
    """
    if isinstance(source, TextArtifact):
        return source
    if isinstance(source, (bytes, bytearray)):
        from .contracts import text_digest_bytes

        payload = bytes(source)
        return TextArtifact(
            artifact_id=artifact_id or "memory",
            digest=text_digest_bytes(payload),
            media_type=media_type or "text/plain",
            byte_length=len(payload),
        )
    path = Path(source)
    return TextArtifact.from_file(
        path,
        artifact_id or path.stem or "text",
        media_type=media_type,
    )


def run_legal_text_evidence(
    source: str | Path | bytes | TextArtifact,
    *,
    artifact_id: str | None = None,
    media_type: str | None = None,
    source_id: str | None = None,
    options: Mapping[str, Any] | None = None,
    reader: TextBackend | None = None,
) -> TextRunResult:
    """Extract legal-text evidence from ``source``.

    Parameters
    ----------
    source:
        A filesystem path, the raw bytes, or a :class:`TextArtifact` you built
        yourself.
    artifact_id:
        Local handle for the artifact. Defaults to the file stem, or ``"memory"``
        for raw bytes. Ignored when ``source`` is already an artifact.
    media_type:
        Declared media type. Defaults to the extension-based guess.
    source_id:
        Identity the emitted units carry. Defaults to the artifact id: units must
        reference a source, and this Skill will not invent one.
    options:
        Skill options. See ``DEFAULT_OPTIONS``.
    reader:
        Alternative reader implementing the Skill's ``TextBackend`` contract.

    Returns
    -------
    TextRunResult
        Units, run diagnostics and the capability statement. A run that found
        nothing still returns a result — with the loss recorded — rather than
        raising.

    Examples
    --------
    ::

        from skills.shanhai import run_legal_text_evidence

        result = run_legal_text_evidence("statute.txt", source_id="statute")
        for unit in result.units:
            print(unit.address.value, unit.loss)
        print(result.is_complete_success)
    """
    artifact = legal_text_artifact(source, artifact_id=artifact_id, media_type=media_type)
    skill = evidence_skill(reader)
    return skill.run(
        artifact,
        source_id=source_id or artifact.artifact_id,
        options=options,
    )
