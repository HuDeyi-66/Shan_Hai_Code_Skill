# ShanHai — Legal Text Evidence

ShanHai is an **independent open-source component** for extracting traceable
evidence from legal text. It reads UTF-8 legal text, detects legal structure, and
emits evidence units with exact character, byte and line spans. It reconstructs
citations that can be re-checked against the artifact, and reports structural
problems as distinct, inspectable outcomes instead of guessing.

Nothing is inferred silently: a value that was not read is reported as loss, a
location that is not unique is reported as ambiguity, and a problem with the
document's structure is reported as a typed diagnostic.

**ShanHai needs nothing but itself.** It has no dependency on any SeaFlow
component, does not import one, and does not require one to be present in any
form. A SeaFlow runtime can integrate it as an official Skill, but that
integration is implemented inside SeaFlow — see [Using it with
SeaFlow](#using-it-with-seaflow).

---

## Install

Standard library only. There is no package to install and no service to start:

```bash
git clone https://github.com/HuDeyi-66/Shan_Hai_Code_Skill
cd Shan_Hai_Code_Skill
python --version        # qualified on Windows with CPython 3.13.14
```

That is the whole installation.

## Use it

One function is the whole required surface:

```python
from skills.shanhai import run_legal_text_evidence

result = run_legal_text_evidence("statute.txt", source_id="statute")

print(result.is_complete_success)          # False if anything was lost
for unit in result.units:
    print(unit.address.value, unit.loss)   # exact location, and what is missing
```

`run_legal_text_evidence` accepts a path, raw bytes, or a `TextArtifact` you
build yourself. It returns a `TextRunResult` carrying the evidence units, the
run diagnostics, and an honest assessment of whether the read was complete.

Lower-level entry points are available if you want to drive the pieces:

```python
from skills.shanhai import ShanHaiLegalTextEvidence, TextArtifact, FixtureTextBackend

artifact = TextArtifact.from_file("statute.txt", "statute")
result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
    artifact, source_id="statute"
)
```

### What comes back

* one evidence unit per article, with character, UTF-8 byte and 1-based line
  coordinates computed from the artifact bytes;
* container units for chapters, and for a document that yielded no provisions;
* structural diagnostics kept distinct: `empty_artifact`, `unsupported_structure`,
  `missing_marker`, `malformed_marker`, `numbering_gap`, `duplicate_marker`,
  `encoding_failure`;
* citations rebuilt from an article, a paragraph or a character span, and
  re-verified against the artifact text;
* ambiguity as a result: a duplicated article marker returns every candidate and
  selects none.

### The contract

The types ShanHai returns are **its own**, declared in
`skills/shanhai/contracts.py`: `TextArtifact`, `TextEvidenceUnit`,
`TextLossKind`, `TextUnitClass`, `TextCitationAddress`, `TextProducer`,
`TextRunResult`, `TextCapability`, `TextSupport`. They describe this Skill's
domain and nothing else. The loss and unit-class vocabularies are stable strings,
so you can compare against them without importing anything.

## Run the tests and the example

```bash
python tests/run_all.py --quiet
python examples/shanhai_legal_text_example.py
```

No runtime, service, sibling checkout or external path is required. A dedicated
isolation suite proves it: it checks that no module under `skills/` imports a
private runtime, that importing the package loads no such module, and that a
fresh interpreter with **only this repository on its path** can run the entry
point and the example.

```bash
python tests/run_all.py     # includes the standalone-isolation suite
```

## Using it with SeaFlow

When a SeaFlow runtime is present, ShanHai operates as an **official SeaFlow
Skill**. The integration is implemented in SeaFlow, which adapts this Skill's
public interface into its own internal model.

The dependency therefore points one way only:

```
SeaFlow (private runtime)  ---adapts--->  ShanHai (this repository)
```

ShanHai never imports SeaFlow, and nothing here changes if you never use SeaFlow
at all.

## Related repositories

| Repository | Role |
| --- | --- |
| [SeaFlow](https://github.com/HuDeyi-66/SeaFlow) | Public informational entry point for the project. Documentation only. |
| [LuoHai](https://github.com/HuDeyi-66/Luo_Hai_Tables_Skill) | The sibling Skill, for structured and tabular evidence. |

LuoHai is a **sibling**, not a dependency. Neither Skill imports the other, in
either direction, and that isolation is asserted by test. The links above are for
discovery only.

## Scope and limitations

* **UTF-8 legal text only.** No PDF, DOCX, OCR or spreadsheets; a format outside
  this Skill's capability is refused rather than attempted.
* **No legal authority.** ShanHai extracts and locates text. It does not verify
  that a provision is in force, applicable or authoritative.
* **No retrieval, ranking or models.** Matching and selection belong to a caller.
* **Qualified on Windows with CPython 3.13.14.** The runtime is standard-library
  only, so nothing pins it to that environment, but other versions and platforms
  have not been qualified.

## License

MIT. See `LICENSE`.

```
Copyright (c) 2026 Peng Wang (Hu Deyi)
```

This license covers this repository. It does not extend to the private SeaFlow
base runtime, which is separately maintained and about which this repository
makes no licensing statement. See `DEPENDENCIES.md`.
