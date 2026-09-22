<p align="center">
  <img src="docs/assets/shanhai-header.png" alt="ShanHai（海珊）" />
</p>

[English](README.md) | [简体中文](README.zh-CN.md)

# ShanHai（海珊）

**Legal Text Evidence Skill**

ShanHai is an independently usable open-source Skill for structured legal and
textual evidence extraction and citation. It reads UTF-8 legal text, detects
legal structure, and emits evidence units carrying exact character, byte and line
spans. It reconstructs citations that can be re-checked against the artifact, and
reports structural problems as distinct, inspectable outcomes instead of
guessing.

Nothing is inferred silently: a value that was not read is reported as loss, a
location that is not unique is reported as ambiguity, and a problem with the
document's structure is reported as a typed diagnostic.

* **Standalone use is a first-class supported mode.** ShanHai can be cloned,
  tested and used without access to the private SeaFlow base runtime.
* **SeaFlow integration is optional.** When integrated with SeaFlow, ShanHai acts
  as an official SeaFlow Skill/plugin — but that integration is implemented on
  SeaFlow's side, and standalone use does not require it.

---

<p align="center">
  <img src="docs/assets/shanhai-comic.png" alt="ShanHai（海珊）Skill comic" />
</p>

## Capabilities

These are the capabilities the Skill declares at runtime. Anything not listed is
not implemented.

| Capability | Support | What it does |
| --- | --- | --- |
| Legal-text evidence units | supported | one evidence unit per detected article, plus container units for chapters, or for a document that yielded no provisions |
| Structural diagnostics | supported | `empty_artifact`, `unsupported_structure`, `missing_marker`, `malformed_marker`, `numbering_gap`, `duplicate_marker`, `encoding_failure` — kept distinct |
| Exact span location | supported | character, UTF-8 byte and 1-based line spans recorded per provision, computed from the artifact bytes |
| Text citation reconstruction | supported | an article, a paragraph or a character span rebuilds to an exact, re-verifiable citation |
| Paragraph splitting | partial | paragraphs are blank-line separated blocks inside an article; a single-paragraph article yields one block |
| Retrieval or ranking | unsupported | no retrieval, ranking, FTS, similarity or fuzzy matching exists in this Skill, by decision |
| OCR and non-text input | unsupported | only UTF-8 text is read; images, PDFs and binary formats are not text artifacts |
| Legal authority | unsupported | this Skill records *where* text is; it makes no claim about whether that text is in force, applicable or authoritative |

Ambiguity is a result, not an error: a duplicated article marker returns every
candidate and selects none. There is no first-match fallback anywhere.

ShanHai does **not** provide legal advice, semantic legal reasoning, LLM
generation, autonomous agents, verified legal authority, or universal
legal-format support.

## Validated Legal-Source Coverage

ShanHai is a **Skill, not a corpus**. This repository ships the extraction
capability; it does not ship the legal texts, and the public repository is not
the owner's private source collection.

The following legal instruments and representations have been used in the
current real-source intake and validation corpus. **The source texts themselves
are not distributed as part of this repository**, so cloning it does not give
you the sources listed below.

**Corpus shape:** 19 legal instruments · 26 representations · 26 hash-bound
artifacts · 18 extraction-eligible · 8 extraction-blocked · 13 `ADMITTED` ·
2 `ADMITTED_WITH_LIMITATIONS` · 11 `REVIEW_REQUIRED`.

Admission is decided **per representation**, not per instrument, so where an
instrument has several representations each one carries its own status. In the
status cells below, the lines correspond to the representations listed in the
same order. A representation blocked by format does not mean the instrument is
unsupported: another representation of the same instrument may hold a different
status. `SAME_INSTRUMENT_DIFFERENT_REPRESENTATION` records that two texts render
one instrument; it does **not** assert `AUTHORITY_EQUIVALENCE` between them, and
no such equivalence is claimed anywhere in this table.

| Legal instrument | Jurisdiction / level | Representation(s) | Current status | Notes |
| --- | --- | --- | --- | --- |
| 中华人民共和国宪法 — Constitution of the PRC | CN · Constitution | Chinese TXT | Chinese TXT — `ADMITTED` | Chapter context limited (GAP-002); article-level evidence unaffected |
| 中华人民共和国刑法 — Criminal Law | CN · NPC law | Chinese TXT<br>English TXT | Chinese TXT — `ADMITTED`<br>English TXT — `REVIEW_REQUIRED` | The English rendering is blocked by representation format (`Article N` Latin headings), not by instrument quality |
| 中华人民共和国刑事诉讼法 — Criminal Procedure Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | Chapter numbering legitimately restarts across its parts (GAP-002); article-level evidence unaffected |
| 中华人民共和国民法典 — Civil Code | CN · NPC law | Chinese TXT | Chinese TXT — `REVIEW_REQUIRED` | GAP-001: 999 of 1260 article markers resolve; articles 1000–1260 are not citable from this representation |
| 中华人民共和国民事诉讼法 — Civil Procedure Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 国内水路运输管理条例 — Regulation on Domestic Water Transport | CN · State Council administrative regulation | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 国内水路运输管理规定 — Provisions on Domestic Water Transport | CN · departmental rule | Chinese TXT | Chinese TXT — `ADMITTED_WITH_LIMITATIONS` | Two non-article enumerated lines are kept as reported lossy fragments; all 58 articles resolve |
| 商业秘密保护规定 — Provisions on Trade Secret Protection | CN · departmental rule | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国反不正当竞争法 — Anti-Unfair Competition Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国仲裁法 — Arbitration Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED_WITH_LIMITATIONS` | The artifact carries a scraped publication page header that is not part of the instrument; all 96 articles resolve |
| 中华人民共和国企业破产法 — Enterprise Bankruptcy Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国反间谍法 — Counter-Espionage Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国网络安全法 — Cybersecurity Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国劳动法 — Labour Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国海上交通安全法 — Maritime Traffic Safety Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 中华人民共和国证券法 — Securities Law | CN · NPC law | Chinese TXT | Chinese TXT — `ADMITTED` | — |
| 承认及执行外国仲裁裁决公约 — New York Convention (1958) | International · UN treaty | Chinese TXT<br>English TXT<br>Chinese PDF<br>English PDF | Chinese TXT — `REVIEW_REQUIRED`<br>English TXT — `REVIEW_REQUIRED`<br>Chinese PDF — `REVIEW_REQUIRED`<br>English PDF — `REVIEW_REQUIRED` | Issuing organ and depositary are not evidenced in these artifacts and the Chinese rendering is not marked as authenticated; the English TXT is blocked by heading format and both PDFs by container format |
| 联合国全程或者部分海上国际货物运输合同公约 — Rotterdam Rules | International · UN treaty | Chinese TXT<br>English TXT<br>Chinese PDF<br>English PDF | Chinese TXT — `REVIEW_REQUIRED`<br>English TXT — `REVIEW_REQUIRED`<br>Chinese PDF — `REVIEW_REQUIRED`<br>English PDF — `REVIEW_REQUIRED` | Line-initial in-prose cross-references make four articles ambiguous for selection (all 96 article numbers still resolve); authority and entry-into-force status unevidenced; the English TXT and both PDFs are blocked |
| UK Public General Act 1995 c.21 (candidate) | UK · foreign national law (candidate) | Scanned PDF | Scanned PDF — `REVIEW_REQUIRED` | Identity/provenance requires further review; scanned-image PDF with no readable text layer, and the filename is not itself evidence of identity |

Instrument level is taken from the promulgating authority evidenced in the
artifact text (`国务院令第…号`, `交通运输部令第…号`, `…会议通过`, `制定本法`),
not from title words such as 法, 条例 or 规定. Judicial interpretations, local
regulations and local government rules are not present in this corpus at all.

### Blocked representations, and what they do not mean

A representation is `EXTRACTION_BLOCKED` when the standalone Skill cannot read
its format or structure: PDF containers (no OCR is performed), scanned-image
PDFs, or English renderings that use `Article N` Latin headings instead of the
Chinese `第X条` markers this Skill targets. That is a statement about one
representation, not about the legal instrument — where the same instrument also
has a supported Chinese TXT rendering, that rendering is assessed separately and
may be admitted. No blocked artifact was converted or OCRed to make the intake
look complete, and no legal identity is inferred from a filename.

### What admission status does — and does not — mean

Admission status describes ShanHai's current evidence-processing state for a
specific representation; it does not by itself determine legal force,
applicability or authority. `ADMITTED` records that a hash-bound,
extraction-eligible representation resolved against an independent article-side
census and carries no recorded authority gap — it does not mean the instrument
is in force, applicable to any particular question, or officially verified.
Inclusion in the validated corpus is **not legal advice**, and query-time
relevance remains conditional on the issue at hand.

## Installation

Standard library only. There is no package to install and no service to start:

```bash
git clone https://github.com/HuDeyi-66/Shan_Hai_Code_Skill
cd Shan_Hai_Code_Skill
python --version        # qualified on Windows with CPython 3.13.14
```

That is the whole installation.

## Minimal standalone example

One function is the whole required surface:

```python
from skills.shanhai import run_legal_text_evidence

result = run_legal_text_evidence("statute.txt", source_id="statute")

print(result.is_complete_success)          # False if anything was lost
for unit in result.units:
    print(unit.address.value, unit.loss)   # exact location, and what is missing
```

`run_legal_text_evidence` accepts a filesystem path, raw bytes, or a
`TextArtifact` you build yourself. It returns a run result carrying the evidence
units, the run diagnostics, and an honest assessment of whether the read was
complete. A document that yielded nothing still returns a result — with the loss
recorded — rather than raising.

Lower-level entry points are available if you want to drive the pieces:

```python
from skills.shanhai import ShanHaiLegalTextEvidence, TextArtifact, FixtureTextBackend

artifact = TextArtifact.from_file("statute.txt", "statute")
result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
    artifact, source_id="statute"
)
```

There is also a runnable example in the repository:

```bash
python examples/shanhai_legal_text_example.py
```

## Testing

```bash
python tests/run_all.py --quiet
```

No runtime, service, sibling checkout or external path is required. A dedicated
isolation suite proves it: it fails if any module under `skills/` acquires an
import of a private runtime, it checks that importing the package loads no such
module, and it runs the entry point and the example from a fresh interpreter
whose path contains **only this repository**.

## Known limitations

* **UTF-8 legal text only.** No PDF, DOCX, OCR or spreadsheets. A format outside
  the Skill's capability is refused rather than attempted.
* **Chinese legal markers.** Article and chapter detection targets numbered
  Chinese markers (`第X条`, `第X章`). `Article N`-style Latin headings are outside
  this Skill's scope and are reported as an unsupported structure.
* **GAP-001 — CJK numerals containing 千 are not resolved.** Some article numbers
  written with Chinese numerals cannot currently be located, so a citation to
  them cannot be resolved. In the validated corpus this affects the Chinese Civil
  Code representation (999 of 1260 article markers resolve; articles 1000–1260
  are not citable from it); the same gap was observed independently on a
  separately maintained representation of the PRC Ecological Environment Code,
  outside this corpus. It is specific to the CJK numeral representation, not to
  article magnitude — the Criminal Law reaches article 452 using half-width
  digits and resolves fully.
* **GAP-002 — table-of-contents / body chapter ambiguity.** Chapter markers
  inside a table of contents and genuine body chapter structures cannot always
  be distinguished reliably, and repeated chapter numbering can be legitimate
  when numbering restarts across Parts. This affects chapter context only:
  article-level evidence is unaffected, and no blind deduplication is performed.
* **UTF-8 only for encoding.** A BOM-less legacy encoding is reported as an
  encoding failure rather than guessed at.
* **Paragraph splitting is partial.** Paragraphs are blank-line separated blocks;
  deeper intra-article structure is not modelled.
* **No retrieval or ranking.** Matching and selection belong to a caller.
* **No legal authority.** Extraction and location only.
* **Platform qualification.** Qualified on Windows with CPython 3.13.14. The
  runtime imports only the standard library, so nothing pins it to that
  environment, but other versions and platforms have not been qualified.

## Relationship with SeaFlow

ShanHai is one of two independently published open-source Skills. SeaFlow can
integrate it as an official Skill/plugin; standalone use does not require access
to the private SeaFlow base runtime.

The dependency runs one way only:

```
SeaFlow (private runtime)  ---adapts--->  ShanHai (this repository)
```

ShanHai never imports SeaFlow. Nothing here changes if you never use SeaFlow.

* SeaFlow public informational entry point:
  <https://github.com/HuDeyi-66/SeaFlow>

The links in this section are **discovery links**, not runtime dependency
declarations.

## Relationship with LuoHai

LuoHai（海珞） — Tabular Evidence Skill — is ShanHai's **sibling Skill**, not a
dependency. Neither Skill imports the other, in either direction, and that
isolation is asserted by test.

* LuoHai repository: <https://github.com/HuDeyi-66/Luo_Hai_Tables_Skill>

## License

MIT. See `LICENSE`.

```
Copyright (c) 2026 Peng Wang (Hu Deyi)
```

This license covers this repository. It does not extend to the private SeaFlow
base runtime, which is separately maintained; this repository makes no licensing
statement about it. See `DEPENDENCIES.md`.
