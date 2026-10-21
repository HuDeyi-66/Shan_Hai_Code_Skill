# Multilingual evidence 1.1.0 — same-stage Cycle2 remediation

This is V3.4-A development, without formal operator exposure. The existing
legacy ShanHai API, v1.0.0 schema files and other Skills remain unchanged.
The opt-in `skills.shanhai.multilingual` module now emits schema/profile1.1.0.
Old results/citations are rejected with `unsupported_schema`; no silent native
address conversion. Original Cycle1 engine/evidence is preserved in the local
historical test snapshot. Regenerating evidence changes profile-bound identities.

Fourteen profile IDs remain; no new national capability is inferred from their
count. French accepts numeric/code labels plus exact `premier`/`1er` first-article
forms; plural/extended words are not equivalent headings. Russian accepts a
bounded nominative `Статья N. Nominal title` layout with visible capitalization
and exclusions for obvious sentence openings; inflected references remain refs.
Arabic accepts observed `(إصدار)` labels in a separate promulgation scope and
does not conflate them with same-number main provisions. These are lexical/layout
rules, not legal-effect or temporal determinations.

Matching normalization v2 removes Arabic tatweel/vowel marks from the matching
view only, with diagnostics and original-anchored many-to-one maps. Original
logical text and UTF-8 bytes remain intact. Suspected visual-order Arabic is
flagged and never silently reversed. Native `marker_span/text` identify the label;
`heading_span/text` retain the complete recognized heading/caption; unit `span`
retains the entire provision. Japanese preceding caption lines are assigned to
the following article, not silently appended to the previous provision.

`analyze_auto` is Mode A: conservative profile proposals, with abstention when
drafting family is ambiguous (including PT/BR). `analyze(profile_id=...)` without
offsets is Mode B. Providing `heading_offsets` is Mode C, conditional source-
position assistance; it is not autonomous discovery. A/C never silently override
a caller's declared profile. No mandatory imports of other Skills or frameworks.

Ranges/relative/fine-grained references may remain explicitly unresolved. Physical
line paragraph candidates are not guaranteed to reproduce source legal hierarchy.
Code/treaty/national/annex families require their own real evidence; synthetic
fixtures and official source oracles are not independent human adjudication.
No universal nine-language accuracy, independent benchmark acceptance, legal
authority, applicability, validity or sufficiency claim is made.

Schemas/profiles: `schemas/multilingual/1.1.0`. Tests:
`python -B -m unittest discover -s tests/multilingual -v`.
All tests inside the Skill use only stdlib. Evaluation/source conversion tooling
remains outside the Skill; cross-Skill conversion remains application-owned.
