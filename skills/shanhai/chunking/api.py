"""Exact-span, bounded primary partition of a qualified immutable representation.

Source qualification and A->R projection verification are external preconditions.
This module validates and binds their records; it cannot authenticate a publisher
or infer legal structure. Only the Python standard library is required.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from bisect import bisect_right
from dataclasses import dataclass

CONTRACT = 'shanhai-source-chunking/1.0.0'
LANGUAGES = ('zh', 'en', 'ja', 'ru', 'fr', 'ar', 'de', 'es', 'pt')
REPRESENTATION = 'shanhai-qualified-representation/1.0.0'
CITATION = 'shanhai-chunk-citation/1.0.0'
HASH = re.compile(r'^[0-9a-f]{64}$')

class ChunkingError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(code + ': ' + detail)

def _require(condition, code, detail):
    if not condition:
        raise ChunkingError(code, detail)

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _stable(value):
    try:
        return _sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False).encode('utf-8'))
    except (ValueError, TypeError, UnicodeError) as error:
        raise ChunkingError('invalid_input', 'JSON-compatible Unicode record required') from error

def _text(raw):
    _require(type(raw) is bytes, 'invalid_input', 'immutable UTF-8 bytes required')
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ChunkingError('encoding_failure', 'strict UTF-8 required') from error

def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())

@dataclass(frozen=True)
class ChunkConfig:
    max_codepoints: int = 1024
    context_codepoints: int = 0

    def as_dict(self):
        _require(type(self.max_codepoints) is int and self.max_codepoints > 0,
                 'invalid_config', 'positive integer max_codepoints required')
        _require(type(self.context_codepoints) is int and
                 0 <= self.context_codepoints <= self.max_codepoints,
                 'invalid_config', 'context must be integer in [0,max_codepoints]')
        return dict(schema='shanhai-chunk-config/1.0.0', unit='unicode_codepoints',
                    max_codepoints=self.max_codepoints, context_codepoints=self.context_codepoints,
                    boundary_policy='furthest_verified_cue_within_hard_budget_else_exact_cap',
                    oversized_policy='split_exact_codepoints_no_exception',
                    combining_policy='may_split_grapheme_preserve_all_codepoints',
                    primary_overlap=0)

def make_representation(raw, *, source_id, artifact_id, artifact_sha256,
                        source_uri, qualification_id, derivation):
    """Bind an externally qualified representation R to acquired artifact A.

    derivation is either identity-utf8 or qualified-external-projection. External
    projections require exact mapping/qualification-receipt digests and explicit
    loss/exclusion/layout records, verified outside this chunker. A reference to
    a receipt is not a claim that ShanHai checked its authority or legal meaning.
    """
    _text(raw)
    record = dict(schema=REPRESENTATION, source_id=source_id, artifact_id=artifact_id,
                  artifact_sha256=artifact_sha256, source_uri=source_uri,
                  source_qualification_id=qualification_id, representation_sha256=_sha(raw),
                  representation_byte_length=len(raw), coordinate_system='R:unicode_codepoints+utf8_bytes',
                  derivation=copy.deepcopy(derivation))
    _validate_representation(raw, record)
    return record

def _validate_representation(raw, record):
    _text(raw)
    _require(isinstance(record, dict), 'invalid_representation', 'record object required')
    fields = {'schema', 'source_id', 'artifact_id', 'artifact_sha256', 'source_uri',
              'source_qualification_id', 'representation_sha256', 'representation_byte_length',
              'coordinate_system', 'derivation'}
    _require(set(record) == fields and record['schema'] == REPRESENTATION,
             'unsupported_representation', 'explicit version adapter required')
    for field in ['source_id', 'artifact_id', 'source_uri', 'source_qualification_id']:
        _require(_nonempty(record[field]), 'invalid_representation', 'missing ' + field)
    _require(isinstance(record['artifact_sha256'], str) and HASH.fullmatch(record['artifact_sha256']),
             'invalid_representation', 'artifact digest required')
    _require(record['representation_sha256'] == _sha(raw) and
             type(record['representation_byte_length']) is int and record['representation_byte_length'] == len(raw),
             'integrity_failure', 'R digest/byte length mismatch')
    _require(record['coordinate_system'] == 'R:unicode_codepoints+utf8_bytes',
             'unsupported_coordinates', 'R coordinates required')
    d = record['derivation']
    _require(isinstance(d, dict) and set(d) == {'schema', 'method', 'artifact_sha256',
             'representation_sha256', 'mapping_sha256', 'qualification_receipt_sha256',
             'exclusions', 'generated_layout', 'information_loss'},
             'invalid_derivation', 'complete derivation manifest binding required')
    _require(d['schema'] == 'shanhai-text-derivation/1.0.0' and
             d['method'] in ('identity-utf8', 'qualified-external-projection'),
             'unsupported_derivation', 'unknown derivation schema/method')
    _require(d['artifact_sha256'] == record['artifact_sha256'] and
             d['representation_sha256'] == _sha(raw), 'integrity_failure', 'A/R derivation identity mismatch')
    for field in ['exclusions', 'generated_layout', 'information_loss']:
        _require(isinstance(d[field], list), 'invalid_derivation', 'explicit list required: ' + field)
    if d['method'] == 'identity-utf8':
        _require(record['artifact_sha256'] == _sha(raw) and d['mapping_sha256'] is None and
                 d['qualification_receipt_sha256'] is None and
                 not any(d[f] for f in ['exclusions', 'generated_layout', 'information_loss']),
                 'invalid_derivation', 'identity representation must be byte-identical and lossless')
    else:
        for field in ['mapping_sha256', 'qualification_receipt_sha256']:
            _require(isinstance(d[field], str) and HASH.fullmatch(d[field]),
                     'invalid_derivation', 'external qualified proof digest required: ' + field)
    _stable(record)

def _cues(cues, size, representation_sha256):
    _require(isinstance(cues, (list, tuple)), 'invalid_cue', 'cue sequence required')
    result = []; ids = set()
    for cue in cues:
        _require(isinstance(cue, dict) and set(cue) == {'position', 'kind', 'verification',
                 'evidence_id', 'evidence_sha256', 'representation_sha256'},
                 'invalid_cue', 'complete technical cue record required')
        _require(type(cue['position']) is int and 0 <= cue['position'] <= size,
                 'invalid_cue', 'codepoint position outside R')
        _require(cue['verification'] in ('independently_verified', 'candidate') and
                 _nonempty(cue['kind']) and _nonempty(cue['evidence_id']) and cue['evidence_id'] not in ids,
                 'invalid_cue', 'typed unique cue identity/verification required')
        _require(cue['representation_sha256'] == representation_sha256 and
                 isinstance(cue['evidence_sha256'], str) and HASH.fullmatch(cue['evidence_sha256']),
                 'integrity_failure', 'cue not bound to qualified R/evidence')
        ids.add(cue['evidence_id']); result.append(copy.deepcopy(cue))
    return sorted(result, key=lambda c: (c['position'], c['evidence_id']))

def _config(value):
    if value is None:
        value = ChunkConfig()
    _require(isinstance(value, ChunkConfig), 'invalid_config', 'ChunkConfig required')
    return value.as_dict()

def _chunk_id(binding, role, order, start, end):
    return _stable(dict(binding=binding, role=role, order=order, char_start=start, char_end=end))

def chunk(raw, *, representation, language, profile_id=None, language_mode='declared',
          config=None, cues=()):
    """Return a disjoint primary partition plus separately marked context slices.

    Verified cues are external source facts; candidates are recorded and ignored.
    Hard cap is codepoints, not words/tokens/graphemes. No source text is changed.
    Automatic language recognition is deliberately not claimed by this interface.
    """
    text = _text(raw); _validate_representation(raw, representation)
    _require(language_mode == 'declared', 'automatic_detection_not_supported', 'supply declared language')
    _require(language in LANGUAGES, 'unsupported_language', 'supported language declaration required')
    expected_profile = language + ':source-faithful-text/1.0.0'
    _require(profile_id is None or profile_id == expected_profile,
             'unsupported_profile', 'language-specific source-text profile required')
    conf = _config(config); cue_records = _cues(cues, len(text), _sha(raw))
    binding = dict(contract=CONTRACT, representation_record_sha256=_stable(representation),
                   representation_sha256=_sha(raw), language=language, profile_id=expected_profile,
                   config_sha256=_stable(conf), cue_records_sha256=_stable(cue_records))
    derivation_sha256 = _stable(representation['derivation'])
    offsets = [0]
    for c in text:
        offsets.append(offsets[-1] + len(c.encode('utf-8')))
    verified = sorted({c['position'] for c in cue_records if c['verification'] == 'independently_verified'})
    primary = []; secondary = []; start = 0
    def emit(a, b, role, order, reason):
        content = text[a:b]
        native = dict(schema=CITATION, binding=copy.deepcopy(binding),
                      artifact_id=representation['artifact_id'], artifact_sha256=representation['artifact_sha256'],
                      source_id=representation['source_id'], derivation_record_sha256=derivation_sha256,
                      role=role, order=order, char_start=a, char_end=b,
                      byte_start=offsets[a], byte_end=offsets[b], text_sha256=_sha(content.encode('utf-8')),
                      chunk_id=_chunk_id(binding, role, order, a, b), reference_target_status='not_assessed')
        return dict(chunk_id=native['chunk_id'], role=role, order=order, text=content,
                    span={k:native[k] for k in ['char_start','char_end','byte_start','byte_end']},
                    boundary_status=reason, legal_unit_type=None, citation=native)
    while start < len(text):
        cap = min(start + conf['max_codepoints'], len(text))
        if cap == len(text):
            end = cap; reason = 'end_of_input'
        else:
            i = bisect_right(verified, cap) - 1
            if i >= 0 and verified[i] > start:
                end = verified[i]; reason = 'verified_source_cue'
            else:
                end = cap
                reason = 'budget_split_without_eligible_verified_cue' if verified else 'no_verified_cues_fallback'
        order = len(primary)
        primary.append(emit(start, end, 'primary', order, reason))
        context = conf['context_codepoints']
        if context and start:
            secondary.append(emit(max(0, start-context), start, 'secondary_context', order, 'declared_preceding_context'))
        start = end
    result = dict(schema=CONTRACT, status='CHUNKED' if text else 'EMPTY_INPUT',
                  representation=copy.deepcopy(representation), binding=binding, language_mode=language_mode,
                  config=conf, cues=cue_records, primary_chunks=primary, secondary_chunks=secondary,
                  coverage=dict(coordinate_system='R:unicode_codepoints+utf8_bytes',
                                retained_codepoints=len(text), retained_bytes=len(raw),
                                primary_codepoints=sum(len(c['text']) for c in primary),
                                primary_partition='disjoint_ordered_full_R', primary_exclusions=[],
                                primary_overlap=0, secondary_in_primary_denominator=False,
                                chunker_generated_layout=[], chunker_information_loss=[]),
                  uncertainty=dict(legal_interpretation='not_assessed', reference_targets='not_assessed',
                                   automatic_language_detection='not_supported',
                                   grapheme_preservation_guaranteed=False,
                                   candidate_cues_ignored=sum(c['verification']=='candidate' for c in cue_records)))
    result['result_sha256'] = _stable(result)
    return result

def validate_result(raw, result):
    _require(isinstance(result, dict) and result.get('schema') == CONTRACT,
             'unsupported_schema', 'versioned chunk result required')
    try:
        conf = result['config']
        rebuilt = chunk(raw, representation=result['representation'], language=result['binding']['language'],
                        profile_id=result['binding']['profile_id'], language_mode=result['language_mode'],
                        config=ChunkConfig(conf['max_codepoints'], conf['context_codepoints']), cues=result['cues'])
        _require(result == rebuilt, 'integrity_failure', 'result changed or incompatible')
        return True
    except (KeyError, TypeError) as error:
        raise ChunkingError('invalid_input', 'malformed result') from error

def citation(result, chunk_id):
    _require(isinstance(result, dict) and result.get('schema') == CONTRACT,
             'unsupported_schema', 'chunk result schema required')
    try:
        matches = [c['citation'] for c in result['primary_chunks'] + result['secondary_chunks'] if c['chunk_id'] == chunk_id]
    except (KeyError, TypeError) as error:
        raise ChunkingError('invalid_input', 'malformed chunk result') from error
    _require(len(matches) == 1, 'missing_chunk' if not matches else 'ambiguous_chunk', 'exact chunk identity required')
    return copy.deepcopy(matches[0])

def reconstruct(raw, result, record):
    """Verify the bound whole result and complete native citation, then exact-slice R."""
    return reconstruct_many(raw, result, [record])[0]

def reconstruct_many(raw, result, records):
    """Batch reconstruction validates the result once, then every complete citation."""
    _require(isinstance(records, (list, tuple)), 'invalid_input', 'citation sequence required')
    validate_result(raw, result)
    lookup = {c['chunk_id']: c['citation'] for c in result['primary_chunks'] + result['secondary_chunks']}
    text = _text(raw); output = []
    try:
        for record in records:
            _require(isinstance(record, dict) and record.get('schema') == CITATION,
                     'unsupported_citation', 'explicit native chunk citation required')
            _require(record.get('chunk_id') in lookup, 'missing_chunk', 'emitted chunk identity required')
            _require(record == lookup[record['chunk_id']], 'integrity_failure', 'citation differs from emitted bound record')
            output.append(text[record['char_start']:record['char_end']])
        return output
    except (KeyError, TypeError) as error:
        raise ChunkingError('invalid_input', 'malformed citation') from error
