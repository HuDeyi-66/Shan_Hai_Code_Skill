# ShanHai evidence operators 1.0.0 — frozen B contract

This additive opt-in API is `skills.shanhai.operators_v1`. Existing APIs,
multilingual schemas and the accepted V3.4-A chunker are unchanged.
The result transport schemas live in `schemas/operators/1.0.0/`.

## Domain, binding and scope

Let R = (immutable UTF-8 bytes, nonempty representation_id). Let P be a
canonical multilingual profile identifier. Let B be SourceBinding(source_id,
representation_id, expected_digest, artifact_id?, require_source_qualification).
Identifiers describe caller assertions, not independent source registration.
The digest is algorithm-qualified SHA-256 over the exact R bytes. Native
coordinates are half-open original Unicode code-point and UTF-8 byte intervals.
There is no normalization of returned source text.

The claimed original artifact identity is retained in B. Analyzer artifact_id
is the R identifier: this operator never quietly equates an original A with a
derived R. No A-to-R evidence verifier is available in version 1.0.0. Such
qualification is `unavailable`; requiring it produces a typed refusal.

## STRUCTURE

Typed mapping:

    Representation × ProfileId × SourceBinding × HeadingOffsets?
        -> StructuralObservationResult

Preconditions: correctly typed domain values; identifiers are nonempty; R's
identifier equals B's identifier; R is UTF-8; digest(R.bytes) equals B's expected
digest; P is supported. Heading offsets are optional caller assertions in native
R code-point coordinates. Existing analyze validates them.

Implementation: `TextView.from_bytes`, `analyze`, and `validate_result` own
Unicode mapping, heading rules, profile interpretation and all source spans.
The wrapper projects existing nodes into typed observations. It adds no parser,
heading rule, hierarchy inference or citation index.

Postconditions for `observed`: each text, marker and heading span is byte-exact
in R; all identities and the verified input digest are retained; heading_basis
is unmodified. A source_declared heading is a `caller_assertion`; every other
heading is a `heuristic_observation`. Parent IDs are retained but their legal
meaning is never verified. Text presence in R is a checked fact; interpreting it
as legal structure is a separate, weaker observation. Identifiers remain
caller asserted even after their binding to R is checked.

No nodes yields `unavailable` with the canonical unsupported_structure
diagnostic. Invalid encoding, profile, offsets, identity or digest and required
source qualification yield `refused` and a typed diagnostic. The result does
not claim complete foreign legal hierarchy, legal authority or temporal force.

## RESOLVE_REFS

Typed mapping:

    Representation × StructuralObservationResult × ReferenceRequest
        -> ReferenceResolutionResult

Request is exactly one native reference observation index, or kind + label +
optional scope. Observation requests cannot override the native context.
Preconditions include all binding conditions above. The complete canonical
analysis is revalidated against R; the entire STRUCTURE wrapper is regenerated
and compared, including its classifications and result identity. Mutating the
analysis and recomputing its checksum is insufficient to pass revalidation.

Label matching delegates to native `resolve`. Candidates are complete native
citations, ordered by (native start, native end, unit_id). Existing citation
contracts retain the digest, profile, original source coordinates and text.
No secondary citation index is maintained.

Successful label resolution is `unique_source_label_match`, never a claim of
substantive legal-reference correctness. Native relative, range, external and
granularity observations yield explicit corresponding non-success states even
when label candidates exist. Native unsupported numbering yields `unsupported`.
Multiple matching labels yield `ambiguous`, missing labels in an existing
scope yield `missing`, and unrecognized scopes yield `unknown_scope`.
A scope-free single label match is `unknown_scope`, retaining both the native
label-search result and its candidates; multiple scope-free matches are
`ambiguous`. Contextual legal uniqueness is always `not_established`.
Malformed requests and unverified or altered analysis yield `refused`.

## Invariants and determinism

For identical domain inputs, canonical implementation version and profile/rule
files, JSON output and result IDs are deterministic. Each result ID hashes the
entire canonical JSON body except result_id. There is no clock, network,
source acquisition, source registration, cross-document/version inference or
private Core or sibling-Skill import. Functions do not mutate arguments.
Nested mappings returned in frozen dataclasses are detached data, not sealed
objects; RESOLVE_REFS revalidates them rather than trusting a frozen outer type.
JSON serialization converts tuple fields to arrays. JSON schemas constrain
transport structure; source integrity is a runtime check, not a schema proof.

These are bounded, tested engineering properties. No formal proof of legal
semantics, parser completeness or cryptographic collision resistance is claimed.

## Acceptance gates

B1: typed/schema-valid output, source binding, source span oracle fidelity in
nine profiles, explicit heuristic/caller/verified-text distinctions, parent
classification, source-qualification refusal and stable IDs.
B2: full analysis/wrapper revalidation; all candidates retained; explicit
missing/unknown/relative/range/external/granularity states; scope-free search
never establishes contextual uniqueness.
Both: original standalone suite, negative input mutation tests, deliberate
implementation-mutant detection, and byte-for-byte preservation of baseline
files. B PASS requires all gates, evaluated separately from C.
