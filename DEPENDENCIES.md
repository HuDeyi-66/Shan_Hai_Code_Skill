# Dependencies

## Runtime

| Component | Classification | Required | Redistributed here |
| --- | --- | --- | --- |
| Python standard library | RUNTIME | yes | no (part of the interpreter) |

**That is the complete list.** ShanHai has no third-party runtime dependency and
no dependency on any SeaFlow component. It does not import a private runtime, and
it does not need one present in any form.

Earlier revisions of this file recorded a dependency on a shared SeaFlow Core
package. That dependency is gone: ShanHai now carries its own contract in
`skills/shanhai/contracts.py`, which is the interface its own capability needs
and nothing more.

## Test-only

| Component | Classification | Required | Redistributed here |
| --- | --- | --- | --- |
| Python standard library (`unittest`) | TEST | yes | no |

No test in this repository requires an external checkout, an environment
variable pointing outside the repository, or a network connection.

## Composition

There is nothing to compose. A fresh clone is a complete, runnable Skill:

```bash
git clone https://github.com/HuDeyi-66/Shan_Hai_Code_Skill
cd Shan_Hai_Code_Skill
python tests/run_all.py --quiet
```

The standalone-isolation suite enforces this: it fails if any module under
`skills/` acquires an import of a private runtime, and it runs the entry point
from a fresh interpreter whose path contains only this repository.

## Licensing

ShanHai-authored code is licensed under the MIT License with the notice
`Copyright (c) 2026 Peng Wang (Hu Deyi)`; see `LICENSE`.

No third-party component is bundled, so there is no third-party notice to
reproduce. This license does not extend to the private SeaFlow base runtime,
which is separately maintained; this repository makes no licensing statement
about it.
