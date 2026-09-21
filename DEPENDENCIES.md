# Dependencies

## Runtime

| Component | Classification | Required | Redistributed here |
| --- | --- | --- | --- |
| Python standard library | RUNTIME | yes | no (part of the interpreter) |
| SeaFlow Core (`core/`) | RUNTIME, sibling repository | yes | **no** — obtained from the SeaFlow repository |

ShanHai's runtime imports only the Python standard library and SeaFlow Core. It
has no third-party runtime dependency, so there is no third-party notice to
reproduce here. Core is deliberately **not** vendored: it has one authoritative
implementation, in the SeaFlow repository.

## Test-only

| Component | Classification | Required | Redistributed here |
| --- | --- | --- | --- |
| SeaFlow Core (`core/`) | TEST, supplied at run time | yes | **no** |
| `python-calamine` | not used by ShanHai | no | no |

The locked `python-calamine` comparison binding is a LuoHai concern. ShanHai
neither imports it nor asserts anything about it.

## Explicit Core composition

ShanHai never guesses where Core is. The suite requires one of:

* `--core-root <dir>` on `tests/run_all.py`, or
* the `SEAFLOW_CORE_ROOT` environment variable pointing at a directory that
  contains `core/` (normally a SeaFlow checkout root).

There is no sibling-directory fallback and no machine-specific path in this
repository. If Core cannot be found, the suite fails immediately with an
explicit message rather than silently skipping.
