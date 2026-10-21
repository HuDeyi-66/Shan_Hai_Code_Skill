# Multilingual evidence 1.0.0

Opt-in module `skills.shanhai.multilingual`; the existing API/fixtures are unchanged.
The JSON schemas and complete profile register live in `schemas/multilingual/1.0.0`.
Input is immutable UTF-8 bytes plus explicit profile, source and artifact handles.
No language classifier overrides the selected profile. Optional `heading_offsets`
are original code-point offsets asserted from the source layout, recorded in the
result and required for identical reconstruction. They must not be guessed from
the desired parse. Without them non-CJK headings require standalone marker lines.

Profiles cover numeric labels in the declared drafting families. Chinese admits
traditional/financial numerals and ten-thousand/hundred-million scales; Japanese
admits repeated inserted suffixes. French code prefixes remain textual IDs;
Portuguese PT and BR are separate declared profiles. Arabic remains in logical
Unicode order; bidi controls and presentation forms affect matching only.

`analyze` returns the original text and digest, located hierarchical candidates,
references, lexical cues and diagnostics. Physical unlabelled body lines become
`paragraph` candidates with `position:N`, not claimed legislative numbering.
Explicit list markers are captured; complex enumeration nesting is bounded and
must be externally verified when it affects interpretation. Title/prose ambiguity
is reported rather than silently upgrading it to a heading. Unsupported syntax
can remain unrecognized; this is not a universal reference-extraction claim.

`resolve(kind,label,scope)` never selects the first duplicate. Reference statuses
distinguish missing, ambiguous, unknown scope and unresolved external/range/
relative/subparagraph targets. Endpoints and reverse chains retain the source
span; this version deliberately does not infer their legal target. Cues identify
wording only, including negations; they do not assert duties or legal effect.

`citation` binds the entire native address. `reconstruct` reparses the original,
verifies the complete result and every citation field, including UTF-8 byte and
code-point spans. Wrong bytes, modified parses or forged fields raise
`ContractError` with a machine-readable code. Input scope is UTF-8; PDF/XML
conversion belongs to intake tooling, not this Skill.

`alignment_candidates` requires an exact-digest declared translation relationship;
same-scope/kind/label matches are structural candidates, never legal equivalence.
Authenticity/authority, source registration, temporal evaluation and cross-Skill
orchestration remain outside ShanHai. V2 integer selectors cannot express this
contract losslessly: there is no silent adapter or schema replacement.

Runtime dependencies: Python standard library only. No reviewed external code
has been copied or vendored. Version changes affecting matching, identity or
coordinates require a new schema/profile version and compatibility fixtures.
Run `python -B -m unittest discover -s tests/multilingual -v` for conformance;
`python -B tests/run_all.py --quiet` also discovers these tests.
