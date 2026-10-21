# Opt-in source-faithful chunking 1.0.0

Import from `skills.shanhai.chunking`. Existing analyzers, evidence units and native
citations are unchanged; chunk citations use their own explicit schema. No sibling
Skill, Core, tokenizer, framework, service or model is required.

The caller supplies strict immutable UTF-8 bytes R, a declared language among
zh/en/ja/ru/fr/ar/de/es/pt, a qualified representation record, optional source cues
and `ChunkConfig(max_codepoints=1024, context_codepoints=0)`. Profile names are
`<language>:source-faithful-text/1.0.0`. They declare source-text handling, not accurate
recognition of every legal drafting family. Automatic language recognition is not
implemented by this interface; requesting it refuses explicitly. Existing
`multilingual.analyze_auto` remains separate and receives no new validation claim.

## Source and representation identities

Digests in this interface are lower-case64-character SHA-256 hex strings. Legacy
prefixed `sha256:` digests and multilingual/provision citation envelopes are not
accepted as chunk citations. Any conversion belongs to an explicit application
adapter; these independently versioned contracts are not silently interchangeable.

Artifact A has source ID, artifact ID, URI, SHA-256 and an external source qualification
decision ID. Representation R has its own UTF-8 SHA, byte length and explicit
coordinate system. `make_representation` validates these bindings and a derivation
record, not a publisher's authenticity or substantive legal correctness.

Derivation schema is `shanhai-text-derivation/1.0.0`: method, A/R hashes, mapping and
qualification-receipt digests, explicit exclusions/generated_layout/information_loss.
`identity-utf8` requires A and R bytes/digests identical, null mapping/receipt and no
loss/layout/exclusion. `qualified-external-projection` requires independently
verified external mapping and qualification-receipt digests. Those external records
must actually be checked by the source qualification layer; a digest string alone
does not establish qualification. ShanHai binds their identities and declarations.

Coordinates in chunks/citations always address R, never raw XML/HTML/JSON bytes.
Entity decoding/generated LF/layout transformations must be disclosed in A→R and
validated separately. The chunker adds no text/layout, exclusions or source loss.

## Partition, cues and budget

Primary chunks form a deterministic ordered disjoint partition of all R, including
BOM, whitespace, preamble and trailing text. Every text is exactly the R interval.
Nested evidence containers are not counted as additional primary coverage. An empty
R returns EMPTY_INPUT with zero chunks and zero counts, not a successful nonempty
sample or a100% metric.

Budget is a strict positive integer count of Unicode codepoints. Bool, zero,
negative, float and string budgets refuse. There are no oversized exceptions or
silent truncation. Long source units split exactly at codepoint limits; this may
split a combining sequence, emoji/ZWJ cluster or bidi sequence between chunks.
Every codepoint and complete UTF-8 encoding is preserved, and reassembly is exact.
Grapheme/visual/word/token preservation is not guaranteed. No normalization occurs.

At each start, if remaining R fits, end at EOF. Otherwise choose the furthest
independently verified cue position in `(start,start+max_codepoints]`; if none exists,
cut at the exact hard limit with explicit fallback reason. The policy may coalesce
multiple small structural regions; it does not promise a chunk at every cue. A
long region without an eligible cue receives the recorded budget fallback. Source
cues bind position, source-observed kind, verification state, unique evidence ID,
evidence digest and R digest. Candidate cues are retained but ignored. The caller
must verify cue evidence externally; the chunker does not relabel model heuristics
as source facts. No article number, legal type, parent hierarchy or target is made up.

Optional preceding context is a separate secondary exact span ending at each
primary start, at most context_codepoints and max_codepoints long. Context must
be an integer in `[0,max_codepoints]`. Its role/order/coordinates are explicit and
it never contributes to primary coverage; deliberate overlap with earlier primary
text is declared. Default context is zero.

## Citations and validation

Chunk IDs bind contract, representation-record/R digest, declared language/profile,
configuration/cue digests, role, order and codepoint interval. A native citation
also binds A/source identity, derivation digest, UTF-8 offsets and exact text hash.
`citation(result,id)` returns a copy. `validate_result(raw,result)` deterministically
rebuilds the bound result; `reconstruct(raw,result,record)` checks the full result
and complete citation before exact extraction. `reconstruct_many` performs that
validation once for a batch. Unknown/missing/mutated identities, versions or
coordinates refuse. Independent acceptance must additionally direct-slice raw R
and verify coverage/budgets/cues without using the chunker as its own oracle.

Reference-target state is `not_assessed`; source-span verification is not resolution
of a legal citation. Authority, applicability, sufficiency and legal semantics are
not assessed. Failure raises ChunkingError with a stable code: invalid_input,
encoding_failure, invalid_config, invalid_representation, unsupported_representation,
unsupported_coordinates, invalid_derivation, unsupported_derivation, invalid_cue,
integrity_failure, unsupported_language, unsupported_profile,
automatic_detection_not_supported, unsupported_schema, unsupported_citation,
missing_chunk or ambiguous_chunk. No partial qualified result is returned.

Source/runtime ownership: acquisition and A→R qualification stay outside this Skill;
orchestration stays in the application. This interface does not imply V3/V3+
completion, general legal understanding, autonomous decisions or navigation control.
