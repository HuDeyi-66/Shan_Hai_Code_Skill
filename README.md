# ShanHai — Legal Text Evidence Skill

ShanHai is the official SeaFlow Skill for **legal-text evidence**. It reads
registered UTF-8 legal text, detects legal structure, emits evidence units with
exact character / byte / line spans, reconstructs citations that can be
re-checked against the artifact, and reports ambiguity or unsupported structure
instead of guessing.

This repository is one of the three public SeaFlow repositories. It is a
**sibling** Skill: it depends on SeaFlow Core and on nothing else in the
SeaFlow family.

| Repository | Role |
| --- | --- |
| [SeaFlow](https://github.com/HuDeyi-66/SeaFlow) | Core runtime and application integration |
| **ShanHai** (this repository) | Legal-text evidence Skill |
| [LuoHai](https://github.com/HuDeyi-66/Luo_Hai_Tables_Skill) | Tabular evidence Skill |

---

## What ShanHai owns

* `skills/shanhai/legal_text_extraction.py` — the Skill (`ShanHai.LegalTextEvidence`) and evidence-unit construction.
* `skills/shanhai/textio.py` — decoding, character/byte/line spans, chapters, articles, paragraphs, structural diagnostics.
* `skills/shanhai/citation.py` — exact text-citation reconstruction, ambiguity and refusal outcomes.
* `skills/shanhai/backends.py` — explicit text-reader contracts and the deterministic fixture backend.
* `fixtures/shanhai/` — deterministic legal-text fixtures, the case manifest and the truth record.
* `tests/shanhai/` — the ShanHai contract, evidence-integrity, fixture and citation suites.
* `examples/shanhai_legal_text_example.py` — offline, deterministic example.
* `docs/LEGAL_TEXT_EVIDENCE.md` — the capability statement.

## What ShanHai does not own

* **Core is not vendored here.** `core/` (artifact identity and digest
  verification, source registration, modality-neutral evidence units, the loss
  vocabulary, the Skill result contract) has exactly one authoritative
  implementation, in the SeaFlow repository. This repository depends on it and
  never copies it.
* **No LuoHai code, fixtures or imports.** ShanHai and LuoHai are siblings and
  are mutually isolated; neither may import the other.
* **No application orchestration.** Query planning, branch routing, evidence
  composition, refusal policy and the Citation Packet belong to SeaFlow's `app/`
  layer. ShanHai does not import it.
* No legal authority finding, no retrieval or ranking, no models, no private
  legal corpus.

## Install and run

ShanHai is standard-library only; there is no package to install. Core is
supplied explicitly at test time — never by a hidden sibling-directory guess.

```bash
git clone https://github.com/HuDeyi-66/SeaFlow        # the Core + runtime repository
git clone https://github.com/HuDeyi-66/Shan_Hai_Code_Skill        # this repository
cd Shan_Hai_Code_Skill
```

Point the suite at the SeaFlow checkout root (the directory that contains
`core/`), then run it:

```bash
python tests/run_all.py --core-root ../<seaflow-checkout> --quiet
# or
SEAFLOW_CORE_ROOT=../<seaflow-checkout> python tests/run_all.py --quiet
```

Run the example and the fixture determinism check:

```bash
SEAFLOW_CORE_ROOT=../<seaflow-checkout> python examples/shanhai_legal_text_example.py
SEAFLOW_CORE_ROOT=../<seaflow-checkout> python fixtures/shanhai/build_text_fixtures.py
```

The public import name is stable:

```python
from skills.shanhai import ShanHaiLegalTextEvidence, FixtureTextBackend
```

## Verify

| Level | Command |
| --- | --- |
| ShanHai alone (Core supplied explicitly) | `python tests/run_all.py --core-root <root> --quiet` |
| Fixture determinism | `python fixtures/shanhai/build_text_fixtures.py` |
| Composite (SeaFlow + ShanHai + LuoHai) | the composite gate in the SeaFlow repository |

## Compatibility

See `SKILL_REFERENCES.json` in the SeaFlow repository — the machine-readable
publication reference that pins this Skill to a SeaFlow baseline commit and
records the compatible SeaFlow revision. It is an informational baseline
document: there is no registry, no dynamic discovery, no marketplace, no
installation metadata and no runtime network fetch anywhere in SeaFlow.

## License

ShanHai-authored code is **licensed under the MIT License**; see `LICENSE`.

```
Copyright (c) 2026 Peng Wang (Hu Deyi)
```

Third-party components keep their own licenses and are not relicensed by this
project. See `DEPENDENCIES.md`.
