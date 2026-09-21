"""ShanHai's own evidence contract.

This module is **ShanHai-owned**. It is the public interface this Skill needs to
do its own job, and it is the only contract the standalone Skill depends on.

Why it exists
-------------
ShanHai is published as an independent open-source component. It must be usable
without any private SeaFlow code, so it cannot import a private runtime contract
and it must not carry a copy of one. What it needs is narrower than an
orchestration runtime: an input artifact whose bytes can be re-verified, one
located unit of legal-text evidence with an explicit loss vocabulary, and a run
result that reports diagnostics honestly.

What is deliberately **not** here, because it belongs to a caller that
orchestrates several sources and several Skills:

* source registration and a source registry;
* authority assessment;
* cross-source retrieval, ranking and composition;
* an application query model.

A runtime that has those concerns adapts this Skill's output into its own model.
The adaptation belongs on that side, so the dependency points inward and this
package stays usable alone.

Vocabulary stability
--------------------
The string values below (``"content"``, ``"empty"``, ``"unsupported"``, ...) are
a published, stable vocabulary. A caller may compare against them by value
without importing this module, which is what keeps the Skill's output
consumable by software that does not want a dependency on ShanHai itself.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "TEXT_DIGEST_ALGORITHM",
    "TEXT_MEDIA_TYPES",
    "TextContractError",
    "TextArtifact",
    "TextLossKind",
    "TextUnitClass",
    "TEXT_PROVENANCE_UNAVAILABLE",
    "TextProducer",
    "TextCitationAddress",
    "TextEvidenceUnit",
    "TextSupport",
    "TextCapability",
    "TextRunWarning",
    "TextRunError",
    "TextFallback",
    "TextRunDiagnostics",
    "TextRunResult",
    "TextEvidenceSkill",
    "text_digest_bytes",
    "text_digest_path",
    "detect_text_media_type",
    "text_loss_priority",
    "text_summarise_loss",
    "find_text_units",
]

TEXT_DIGEST_ALGORITHM = "sha256"

#: Media types this Skill can be handed. Extension-based only: the Skill does
#: not sniff content, and does not upgrade a claim because bytes "look like"
#: something else.
TEXT_MEDIA_TYPES: Mapping[str, str] = {
    ".txt": "text/plain",
    ".text": "text/plain",
    ".md": "text/markdown",
}

TEXT_PROVENANCE_UNAVAILABLE = "provenance_unavailable"


class TextContractError(ValueError):
    """Raised when an artifact or unit cannot be described honestly."""


def text_digest_bytes(payload: bytes, algorithm: str = TEXT_DIGEST_ALGORITHM) -> str:
    """Hex content digest. Deterministic, offline, no I/O."""
    return hashlib.new(algorithm, payload).hexdigest()


def text_digest_path(path: str | Path, algorithm: str = TEXT_DIGEST_ALGORITHM) -> str:
    """Digest a file by streaming it, so a large input does not blow up memory."""
    digest = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_text_media_type(path: str | Path) -> str:
    """Media type from the filename extension, or ``application/octet-stream``."""
    return TEXT_MEDIA_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


@dataclass
class TextArtifact:
    """The concrete bytes ShanHai was handed, plus an integrity record.

    This is deliberately *not* "the document". The same legal material may
    arrive as several artifacts, and the bytes are what a citation is re-checked
    against. ``digest`` is computed from those bytes; ``location`` is an
    observation about where they were found and carries no authority.
    """

    artifact_id: str
    digest: str
    digest_algorithm: str = TEXT_DIGEST_ALGORITHM
    media_type: str = "application/octet-stream"
    byte_length: int = 0
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise TextContractError("artifact_id must be a non-empty local handle")
        if not self.digest:
            raise TextContractError(
                "digest must be recorded; a digest-free artifact cannot be "
                "integrity-checked"
            )
        if self.byte_length < 0:
            raise TextContractError("byte_length must not be negative")

    @property
    def content_digest(self) -> str:
        """Algorithm-qualified digest: the only form safe to compare or print."""
        return f"{self.digest_algorithm}:{self.digest}"

    def verify_bytes(self, payload: bytes) -> bool:
        """Re-check a byte payload. Returns False rather than raising.

        An integrity mismatch is a result, not an exception.
        """
        return text_digest_bytes(payload, self.digest_algorithm) == self.digest

    def verify_file(self, path: str | Path) -> bool:
        """Re-check a file on disk against the recorded digest."""
        return text_digest_path(path, self.digest_algorithm) == self.digest

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "digest": self.digest,
            "digest_algorithm": self.digest_algorithm,
            "content_digest": self.content_digest,
            "media_type": self.media_type,
            "byte_length": self.byte_length,
            "location": self.location,
            "integrity_observed": "digest",
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TextArtifact":
        payload = dict(data)
        payload.pop("content_digest", None)
        payload.pop("integrity_observed", None)
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        extra = {k: v for k, v in payload.items() if k not in known}
        payload = {k: v for k, v in payload.items() if k in known}
        if extra:
            payload["metadata"] = {**payload.get("metadata", {}), "_unknown_fields": extra}
        return cls(**payload)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        artifact_id: str,
        *,
        media_type: str | None = None,
    ) -> "TextArtifact":
        """Describe a file on disk. Reads bytes; writes nothing."""
        file_path = Path(path)
        if not file_path.is_file():
            raise TextContractError(f"artifact path is not a readable file: {file_path}")
        return cls(
            artifact_id=artifact_id,
            digest=text_digest_path(file_path),
            media_type=media_type or detect_text_media_type(file_path),
            byte_length=file_path.stat().st_size,
            location=str(file_path),
        )


class TextLossKind:
    """Closed vocabulary for "something is not simply present".

    These are deliberately distinct. A reader must not collapse failed,
    unresolved, empty and absent content into the same clean-looking value.
    """

    #: The location exists but carries no value, and it was marked blank.
    EMPTY = "empty"

    #: The document does not contain the requested location at all.
    ABSENT = "absent"

    #: The reader found nothing, without claiming nothing exists.
    NOT_DETECTED = "not_detected"

    #: Structure or feature is outside this Skill's declared capability.
    UNSUPPORTED = "unsupported"

    #: The concept does not apply here. Recording that is honest; inventing a
    #: value is not.
    NOT_APPLICABLE = "not_applicable"

    #: Content exists but could not be read, and the failure is attributable.
    FAILED = "failed"

    #: A value is present whose interpretation is undetermined.
    UNKNOWN = "unknown"

    #: Content or structure present in the artifact did not survive extraction.
    SILENT_LOSS_RISK = "silent_loss_risk"

    #: The reader is known to conflate this state with another. Declared, never
    #: inferred.
    COLLAPSE_RISK = "collapse_risk"

    ALL = (
        EMPTY,
        ABSENT,
        NOT_DETECTED,
        UNSUPPORTED,
        NOT_APPLICABLE,
        FAILED,
        UNKNOWN,
        SILENT_LOSS_RISK,
        COLLAPSE_RISK,
    )


class TextUnitClass:
    """What kind of thing one unit of legal-text evidence is.

    ``CONTENT`` is a located provision. ``CONTAINER`` is a chapter or a
    document-level observation: it carries structure, not a citable provision.
    """

    CONTENT = "content"
    CONTAINER = "container"
    UNCLASSIFIED = "unclassified"

    ALL = (CONTENT, CONTAINER, UNCLASSIFIED)


#: Most severe first; used when several unit-level losses must be summarised.
_TEXT_LOSS_SEVERITY = (
    TextLossKind.FAILED,
    TextLossKind.SILENT_LOSS_RISK,
    TextLossKind.COLLAPSE_RISK,
    TextLossKind.UNSUPPORTED,
    TextLossKind.ABSENT,
    TextLossKind.EMPTY,
    TextLossKind.NOT_DETECTED,
    TextLossKind.UNKNOWN,
    TextLossKind.NOT_APPLICABLE,
)


def text_loss_priority(loss: str) -> int:
    """Sort key: lower is more severe. Unknown kinds sort last."""
    try:
        return _TEXT_LOSS_SEVERITY.index(loss)
    except ValueError:
        return len(_TEXT_LOSS_SEVERITY)


@dataclass
class TextCitationAddress:
    """Where a unit sits, in enough detail to rebuild a citation.

    The coordinate system is named by the Skill (character, byte and line spans
    are ShanHai's own axes) and the container is a chapter or article marker.
    """

    kind: str
    value: str | None = None
    container_id: str | None = None
    container_label: str | None = None
    context_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("TextCitationAddress.kind is required (coordinate system)")
        self.context_path = tuple(self.context_path)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "container_id": self.container_id,
            "container_label": self.container_label,
            "context_path": list(self.context_path),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TextCitationAddress":
        payload = dict(data)
        payload["context_path"] = tuple(payload.get("context_path") or ())
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in payload.items() if k in known})


@dataclass
class TextProducer:
    """Which ShanHai build produced a unit, through which reader path."""

    skill_id: str
    skill_version: str = "provisional"
    backend_id: str | None = None
    backend_version: str | None = None
    run_id: str | None = None
    method: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "run_id": self.run_id,
            "method": self.method,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TextProducer":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in dict(data).items() if k in known})  # type: ignore[arg-type]


@dataclass
class TextEvidenceUnit:
    """One locatable, citable unit of legal-text evidence.

    ``content`` is the minimal extracted representation; ``content_raw`` is what
    the document literally held; ``content_rendered`` is what a reader would
    display. They are never silently collapsed into one when they differ.

    ``payload`` carries ShanHai's own domain detail (chapter and article
    markers, spans, paragraph list) because it is legal-text-specific and
    belongs to this Skill rather than to any generic vocabulary.
    """

    unit_id: str
    unit_class: str
    source_id: str
    artifact_id: str
    producer: TextProducer
    address: TextCitationAddress
    content: Any = None
    content_raw: Any = None
    content_rendered: Any = None
    provenance: Any = TEXT_PROVENANCE_UNAVAILABLE
    uncertainty: float | None = None
    loss: tuple[str, ...] = ()
    self_warnings: tuple[str, ...] = ()
    self_errors: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.unit_id:
            raise ValueError("TextEvidenceUnit.unit_id is required")
        if self.unit_class not in TextUnitClass.ALL:
            raise ValueError(f"unknown unit_class: {self.unit_class!r}")
        if not self.source_id or not self.artifact_id:
            raise ValueError("a unit must reference both a source and an artifact")
        if not isinstance(self.producer, TextProducer):
            self.producer = TextProducer.from_dict(self.producer)  # type: ignore[arg-type]
        if not isinstance(self.address, TextCitationAddress):
            self.address = TextCitationAddress.from_dict(self.address)  # type: ignore[arg-type]
        self.loss = tuple(self.loss)
        unknown = [k for k in self.loss if k not in TextLossKind.ALL]
        if unknown:
            raise ValueError(f"unknown loss kinds: {unknown!r}")
        self.self_warnings = tuple(self.self_warnings)
        self.self_errors = tuple(self.self_errors)
        if self.uncertainty is not None and not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be within [0.0, 1.0] when present")

    @property
    def is_complete(self) -> bool:
        """True only when the unit claims no loss and no unit-level failure."""
        return not self.loss and not self.self_errors

    @property
    def has_collapse_risk(self) -> bool:
        return (
            TextLossKind.COLLAPSE_RISK in self.loss
            or TextLossKind.SILENT_LOSS_RISK in self.loss
        )

    @property
    def most_severe_loss(self) -> str | None:
        if not self.loss:
            return None
        return sorted(self.loss, key=text_loss_priority)[0]

    @property
    def provenance_is_recorded(self) -> bool:
        return self.provenance not in (None, "", TEXT_PROVENANCE_UNAVAILABLE)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "shanhai-evidence-unit/v1",
            "unit_id": self.unit_id,
            "unit_class": self.unit_class,
            "source_id": self.source_id,
            "artifact_id": self.artifact_id,
            "producer": self.producer.as_dict(),
            "address": self.address.as_dict(),
            "content": self.content,
            "content_raw": self.content_raw,
            "content_rendered": self.content_rendered,
            "provenance": self.provenance,
            "uncertainty": self.uncertainty,
            "loss": list(self.loss),
            "self_warnings": list(self.self_warnings),
            "self_errors": list(self.self_errors),
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TextEvidenceUnit":
        payload = dict(data)
        payload.pop("schema", None)
        payload["producer"] = TextProducer.from_dict(payload["producer"])
        payload["address"] = TextCitationAddress.from_dict(payload["address"])
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        extra = {k: v for k, v in payload.items() if k not in known}
        payload = {k: v for k, v in payload.items() if k in known}
        if extra:
            payload["metadata"] = {**payload.get("metadata", {}), "_unknown_fields": extra}
        return cls(**payload)


def text_summarise_loss(units: Iterable[TextEvidenceUnit]) -> dict[str, int]:
    """Count loss kinds across units, most severe first in the result."""
    counts: dict[str, int] = {}
    for unit in units:
        for kind in unit.loss:
            counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def find_text_units(
    units: Sequence[TextEvidenceUnit],
    *,
    unit_class: str | None = None,
    artifact_id: str | None = None,
    container_id: str | None = None,
) -> tuple[TextEvidenceUnit, ...]:
    """Tiny in-memory filter. This is not retrieval and it does not rank."""
    out = []
    for unit in units:
        if unit_class is not None and unit.unit_class != unit_class:
            continue
        if artifact_id is not None and unit.artifact_id != artifact_id:
            continue
        if container_id is not None and unit.address.container_id != container_id:
            continue
        out.append(unit)
    return tuple(out)


# -- run result ---------------------------------------------------------------


class TextSupport:
    """How well a reader path supports a named capability."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"

    ALL = (SUPPORTED, PARTIAL, UNSUPPORTED, UNKNOWN)


@dataclass
class TextCapability:
    """One named capability of one reader path.

    ``collapse_risks`` is the important field: it lists the loss kinds this path
    is *known* to conflate with a clean value. A path that declares a collapse
    risk must surface it somewhere in the run, or the result is downgraded --
    which is how "a known silent-loss case must not read as complete success" is
    enforced mechanically rather than by good intentions.
    """

    name: str
    support: str = TextSupport.UNKNOWN
    detail: str = ""
    collapse_risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.support not in TextSupport.ALL:
            raise ValueError(f"unknown support level: {self.support!r}")
        self.collapse_risks = tuple(self.collapse_risks)
        unknown = [k for k in self.collapse_risks if k not in TextLossKind.ALL]
        if unknown:
            raise ValueError(f"unknown collapse risk kinds: {unknown!r}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "support": self.support,
            "detail": self.detail,
            "collapse_risks": list(self.collapse_risks),
        }


@dataclass
class TextRunWarning:
    """A run-level notice. Not a failure, but not silence either."""

    code: str
    message: str
    scope: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "scope": self.scope}


@dataclass
class TextRunError:
    """A run-level failure. Errors are attributable, not thrown away."""

    code: str
    message: str
    scope: str | None = None
    fatal: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "scope": self.scope,
            "fatal": self.fatal,
        }


@dataclass
class TextFallback:
    """A recorded degradation. There is no silent fallback."""

    from_backend: str
    to_backend: str
    reason: str
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_backend": self.from_backend,
            "to_backend": self.to_backend,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass
class TextRunDiagnostics:
    """Everything true of the whole run and of no single unit."""

    warnings: list[TextRunWarning] = field(default_factory=list)
    errors: list[TextRunError] = field(default_factory=list)
    unsupported_capabilities: list[str] = field(default_factory=list)
    fallbacks: list[TextFallback] = field(default_factory=list)
    backend_id: str | None = None
    backend_version: str | None = None
    backend_path: str | None = None
    considered_backends: list[str] = field(default_factory=list)
    known_collapse_risks: list[str] = field(default_factory=list)
    #: Loss kinds actually observed at item level on this run. This is what makes
    #: "a declared collapse risk must be surfaced" checkable.
    observed_loss_kinds: list[str] = field(default_factory=list)
    options_echo: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)

    def warn(self, code: str, message: str, scope: str | None = None) -> None:
        self.warnings.append(TextRunWarning(code=code, message=message, scope=scope))

    def error(
        self, code: str, message: str, scope: str | None = None, fatal: bool = False
    ) -> None:
        self.errors.append(
            TextRunError(code=code, message=message, scope=scope, fatal=fatal)
        )

    def fallback(
        self,
        from_backend: str,
        to_backend: str,
        reason: str,
        detail: str | None = None,
    ) -> None:
        self.fallbacks.append(
            TextFallback(
                from_backend=from_backend,
                to_backend=to_backend,
                reason=reason,
                detail=detail,
            )
        )

    @property
    def has_fatal_error(self) -> bool:
        return any(e.fatal for e in self.errors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "warnings": [w.as_dict() for w in self.warnings],
            "errors": [e.as_dict() for e in self.errors],
            "unsupported_capabilities": list(self.unsupported_capabilities),
            "fallbacks": [f.as_dict() for f in self.fallbacks],
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "backend_path": self.backend_path,
            "considered_backends": list(self.considered_backends),
            "known_collapse_risks": list(self.known_collapse_risks),
            "observed_loss_kinds": list(self.observed_loss_kinds),
            "options_echo": self.options_echo,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TextRunDiagnostics":
        diag = cls()
        diag.warnings = [TextRunWarning(**w) for w in data.get("warnings", [])]
        diag.errors = [TextRunError(**e) for e in data.get("errors", [])]
        diag.unsupported_capabilities = list(data.get("unsupported_capabilities", []))
        diag.fallbacks = [TextFallback(**f) for f in data.get("fallbacks", [])]
        diag.backend_id = data.get("backend_id")
        diag.backend_version = data.get("backend_version")
        diag.backend_path = data.get("backend_path")
        diag.considered_backends = list(data.get("considered_backends", []))
        diag.known_collapse_risks = list(data.get("known_collapse_risks", []))
        diag.observed_loss_kinds = list(data.get("observed_loss_kinds", []))
        diag.options_echo = dict(data.get("options_echo", {}))
        diag.stats = dict(data.get("stats", {}))
        return diag


@dataclass
class TextRunResult:
    """Output of one explicit ShanHai invocation.

    ``is_complete_success`` is the only sanctioned way to ask "did this fully
    work?". It is deliberately strict: a run that reports any loss is not a
    complete success, because "no error was raised" must not be readable as "the
    document was read in full".
    """

    artifact: TextArtifact
    skill_id: str
    producer: Any  # TextProducer; loose to avoid a circular import
    units: tuple[TextEvidenceUnit, ...] = ()
    diagnostics: TextRunDiagnostics = field(default_factory=TextRunDiagnostics)
    invocation_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    @property
    def unsurfaced_risks(self) -> tuple[str, ...]:
        """Declared collapse risks with no matching signal in this run."""
        surfaced = set(self.diagnostics.observed_loss_kinds)
        surfaced.update(text_summarise_loss(self.units))
        missing: list[str] = []
        for risk in self.diagnostics.known_collapse_risks:
            if risk in surfaced:
                continue
            if (
                risk == TextLossKind.COLLAPSE_RISK
                and self.diagnostics.unsupported_capabilities
            ):
                continue
            missing.append(risk)
        return tuple(missing)

    def downgrade_for_declared_risk(self) -> list[TextRunWarning]:
        """Turn unsurfaced declared risks into explicit run warnings."""
        added: list[TextRunWarning] = []
        existing = {w.code for w in self.diagnostics.warnings}
        for risk in self.unsurfaced_risks:
            code = f"declared_risk_not_surfaced:{risk}"
            if code in existing:
                continue
            warning = TextRunWarning(
                code=code,
                message=(
                    f"reader path is known to conflate {risk!r} with a clean "
                    f"value, but no unit in this run reports {risk!r}; treat "
                    f"affected values as unverified"
                ),
                scope=self.diagnostics.backend_id,
            )
            self.diagnostics.warnings.append(warning)
            added.append(warning)
            existing.add(code)
        return added

    @property
    def producer_disagreement(self) -> tuple[str, ...]:
        """Unit producers that do not match the run producer."""
        run_backend = self.diagnostics.backend_id
        mismatched = []
        for unit in self.units:
            if unit.producer.backend_id and run_backend:
                if unit.producer.backend_id != run_backend:
                    mismatched.append(
                        f"{unit.unit_id}:{unit.producer.backend_id}!={run_backend}"
                    )
        return tuple(mismatched)

    @property
    def has_no_fatal_condition(self) -> bool:
        """No errors and no unsurfaced declared risk."""
        return not self.diagnostics.errors and not self.unsurfaced_risks

    @property
    def is_complete_success(self) -> bool:
        """True only when the run neither failed nor lost anything."""
        if not self.has_no_fatal_condition:
            return False
        if self.diagnostics.observed_loss_kinds:
            return False
        return all(unit.is_complete for unit in self.units)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "shanhai-run-result/v1",
            "invocation_id": self.invocation_id,
            "skill_id": self.skill_id,
            "producer": self.producer.as_dict()
            if hasattr(self.producer, "as_dict")
            else dict(self.producer),
            "artifact": self.artifact.as_dict(),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "diagnostics": self.diagnostics.as_dict(),
            "units": [u.as_dict() for u in self.units],
            "assessment": {
                "is_complete_success": self.is_complete_success,
                "has_no_fatal_condition": self.has_no_fatal_condition,
                "unsurfaced_declared_risks": list(self.unsurfaced_risks),
                "producer_disagreement": list(self.producer_disagreement),
                "loss_summary": text_summarise_loss(self.units),
            },
        }


class TextEvidenceSkill:
    """The minimal explicit Skill interface ShanHai implements.

    Wiring is by constructor. There is no scanning, no decorator registry and no
    dynamic plugin loading: a caller constructs the Skill it wants.

    Implementations must be read-only with respect to the artifact. A Skill that
    mutates its input destroys the integrity record that makes the evidence
    re-checkable.
    """

    #: Stable identity, e.g. ``"ShanHai.LegalTextEvidence"``.
    skill_id: str = "unnamed.TextSkill"

    #: Provisional version tag. Bumped when observable output changes.
    skill_version: str = "provisional"

    def capabilities(self) -> tuple[TextCapability, ...]:
        """Declare the supported and unsupported capability of this instance."""
        raise NotImplementedError

    def run(
        self,
        artifact: TextArtifact,
        *,
        source_id: str | None = None,
        options: Mapping[str, Any] | None = None,
        source: Any = None,
    ) -> TextRunResult:
        """Extract evidence from an artifact. Read-only."""
        raise NotImplementedError

    def _capability_map(self) -> dict[str, TextCapability]:
        return {c.name: c for c in self.capabilities()}

    def unsupported_capability_names(self) -> list[str]:
        return [
            c.name
            for c in self.capabilities()
            if c.support in (TextSupport.UNSUPPORTED, TextSupport.PARTIAL)
        ]

    def declared_collapse_risks(self) -> list[str]:
        risks: list[str] = []
        for cap in self.capabilities():
            for risk in cap.collapse_risks:
                if risk not in risks:
                    risks.append(risk)
        return risks

    def describe(self) -> dict[str, Any]:
        """Machine-readable capability statement."""
        return {
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "capabilities": [c.as_dict() for c in self.capabilities()],
        }
