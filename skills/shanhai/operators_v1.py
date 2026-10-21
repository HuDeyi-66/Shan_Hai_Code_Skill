"""Opt-in STRUCTURE and RESOLVE_REFS, contract 1.0.0. No legal inference."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .multilingual.analyzer import analyze, citation, resolve, stable, validate_result
from .multilingual.integrity import ContractError, TextView, digest

VERSION = '1.0.0'
StructureState = Literal['observed', 'unavailable', 'refused']
ReferenceState = Literal['unique_source_label_match', 'ambiguous', 'missing',
                         'unknown_scope', 'relative', 'range', 'external',
                         'unsupported', 'granularity_unresolved', 'refused']


@dataclass(frozen=True)
class Representation:
    raw: bytes
    representation_id: str


@dataclass(frozen=True)
class SourceBinding:
    source_id: str
    representation_id: str
    expected_digest: str
    artifact_id: str | None = None
    require_source_qualification: bool = False


@dataclass(frozen=True)
class Diagnostic:
    code: str
    detail: str


@dataclass(frozen=True)
class StructuralObservation:
    unit_id: str
    kind: str
    label: str
    scope: str
    parent_id: str | None
    span: dict[str, int]
    heading_span: dict[str, int]
    marker_span: dict[str, int]
    text: str
    heading_text: str
    marker_text: str
    heading_basis: str
    structure_basis: Literal['caller_assertion', 'heuristic_observation']
    text_basis: str = 'R_bytes_verified'
    parent_basis: str = 'heuristic_observation'


@dataclass(frozen=True)
class StructuralObservationResult:
    schema: str
    operator: str
    status: StructureState
    binding: SourceBinding
    input_digest: str | None
    observations: tuple[StructuralObservation, ...]
    analysis: dict[str, Any] | None
    diagnostics: tuple[Diagnostic, ...]
    source_qualification: str = 'unavailable'
    identity_basis: str = 'caller_asserted_identifiers_bound_to_verified_R_digest'
    result_id: str = ''

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceRequest:
    observation_index: int | None = None
    kind: str | None = None
    label: str | None = None
    scope: str | None = None


@dataclass(frozen=True)
class ReferenceResolutionResult:
    schema: str
    operator: str
    status: ReferenceState
    binding: SourceBinding
    analysis_id: str
    request: ReferenceRequest
    reference: dict[str, Any] | None
    candidates: tuple[dict[str, Any], ...]
    label_search_status: str | None
    diagnostics: tuple[Diagnostic, ...]
    provenance: str = 'revalidated_analysis_and_native_R_citations'
    legal_reference_correctness: str = 'not_assessed'
    contextual_uniqueness: str = 'not_established'
    result_id: str = ''

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _identify(result):
    from dataclasses import replace
    body = result.as_dict()
    body.pop('result_id')
    return replace(result, result_id=stable(body))


def _check_binding(r: Representation, binding: SourceBinding) -> None:
    if not isinstance(r, Representation) or not isinstance(binding, SourceBinding):
        raise ContractError('invalid_input', 'Representation and SourceBinding required')
    if any(not isinstance(x, str) or not x for x in
           (binding.source_id, binding.representation_id, binding.expected_digest, r.representation_id)):
        raise ContractError('invalid_input', 'nonempty bound identifiers and digest required')
    if r.representation_id != binding.representation_id:
        raise ContractError('representation_mismatch', 'R identity differs from binding')
    TextView.from_bytes(r.raw)
    if digest(r.raw) != binding.expected_digest:
        raise ContractError('integrity_failure', 'R digest mismatch')
    if binding.require_source_qualification:
        raise ContractError('source_qualification_unavailable', 'no qualified A-to-R derivation verifier in this operator')


def structure(r: Representation, profile_id: str, binding: SourceBinding, *,
              heading_offsets: list[int] | tuple[int, ...] | None = None) -> StructuralObservationResult:
    """Verify R bytes; delegate observations. Identifiers remain caller assertions."""
    try:
        _check_binding(r, binding)
        analysis = analyze(r.raw, profile_id=profile_id, artifact_id=r.representation_id,
                           source_id=binding.source_id, expected_digest=binding.expected_digest,
                           heading_offsets=heading_offsets)
        validate_result(r.raw, analysis)
        observations = tuple(StructuralObservation(
            **{k: deepcopy(n[k]) for k in ('unit_id', 'kind', 'label', 'scope', 'parent_id',
                 'span', 'heading_span', 'marker_span', 'text', 'heading_text', 'marker_text', 'heading_basis')},
            structure_basis='caller_assertion' if n['heading_basis'] == 'source_declared' else 'heuristic_observation')
            for n in analysis['nodes'])
        diagnostics = tuple(Diagnostic(d['code'], f"R characters [{d['char_start']},{d['char_end']})")
                            for d in analysis['diagnostics'])
        return _identify(StructuralObservationResult('shanhai-structure/1.0.0', 'STRUCTURE',
            'observed' if observations else 'unavailable', binding, digest(r.raw), observations,
            analysis, diagnostics))
    except ContractError as exc:
        return _identify(StructuralObservationResult('shanhai-structure/1.0.0', 'STRUCTURE',
            'refused', binding, None, (), None, (Diagnostic(exc.code, str(exc)),)))


def resolve_refs(r: Representation, verified_analysis: StructuralObservationResult,
                 request: ReferenceRequest) -> ReferenceResolutionResult:
    """Reverify full analysis and wrapper; retain every native label candidate."""
    binding = verified_analysis.binding
    def output(status, reference=None, candidates=(), search=None, diagnostics=()):
        return _identify(ReferenceResolutionResult('shanhai-reference-resolution/1.0.0',
            'RESOLVE_REFS', status, binding, verified_analysis.result_id, request,
            reference, candidates, search, diagnostics))
    try:
        _check_binding(r, binding)
        analysis = verified_analysis.analysis
        if verified_analysis.status == 'refused' or analysis is None:
            raise ContractError('unverified_analysis', 'successful STRUCTURE binding required')
        validate_result(r.raw, analysis)
        if analysis['artifact_id'] != r.representation_id or analysis['source_id'] != binding.source_id:
            raise ContractError('representation_mismatch', 'analysis identity differs from R binding')
        rebuilt = structure(r, analysis['profile']['profile_id'], binding, heading_offsets=analysis['heading_offsets'])
        if rebuilt != verified_analysis:
            raise ContractError('integrity_failure', 'structural wrapper altered')
        if not isinstance(request, ReferenceRequest):
            raise ContractError('invalid_input', 'ReferenceRequest required')
        reference = None
        if request.observation_index is not None:
            index = request.observation_index
            if any(x is not None for x in (request.kind, request.label, request.scope)):
                raise ContractError('invalid_input', 'observation and label request are exclusive')
            if type(index) is not int or not 0 <= index < len(analysis['references']):
                raise ContractError('invalid_input', 'reference index outside analysis')
            reference = deepcopy(analysis['references'][index])
            kind, label, scope = (reference[k] for k in ('kind', 'label', 'scope'))
            if kind == 'relative':
                return output('relative', reference)
            if label is None:
                return output('unsupported', reference)
        else:
            kind, label, scope = request.kind, request.label, request.scope
        search = resolve(analysis, kind=kind, label=label, scope=scope)
        # Native source order, with unit identity as a deterministic tie-breaker.
        targets = [n for n in analysis['nodes'] if n['unit_id'] in search['candidates']]
        targets.sort(key=lambda n: (n['span']['char_start'], n['span']['char_end'], n['unit_id']))
        candidates = tuple(citation(analysis, n['unit_id']) for n in targets)
        native_states = {'external_unresolved': 'external', 'range_unresolved': 'range',
                         'granularity_unresolved': 'granularity_unresolved', 'unsupported_number': 'unsupported'}
        if reference and reference['status'] in native_states:
            status = native_states[reference['status']]
        elif scope is None:
            status = 'ambiguous' if len(candidates) > 1 else 'unknown_scope'
        elif scope not in {n['scope'] for n in analysis['nodes']}:
            status = 'unknown_scope'
        else:
            status = {'resolved': 'unique_source_label_match', 'ambiguous': 'ambiguous', 'missing': 'missing'}[search['status']]
        return output(status, reference, candidates, search['status'])
    except ContractError as exc:
        return output('refused', diagnostics=(Diagnostic(exc.code, str(exc)),))


STRUCTURE = structure
RESOLVE_REFS = resolve_refs
