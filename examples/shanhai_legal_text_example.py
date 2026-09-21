"""ShanHai example: legal text evidence and citation.

Run from the repository root::

    python examples/shanhai_legal_text_example.py

Reads a committed synthetic fixture (a short excerpt of Chinese maritime
legislation, authored for this repository), registers it as a source/artifact,
extracts evidence units, and reconstructs one exact citation. Every path is
relative to this repository, and nothing is downloaded.

What to look for:

* each detected article becomes one evidence unit with character, byte and line
  coordinates;
* a citation is rebuilt from the unit and re-verified against the artifact text;
* a query for a duplicated article marker returns ambiguity rather than choosing.
"""

from __future__ import annotations

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.artifact import Artifact  # noqa: E402
from core.source import SourceRegistry  # noqa: E402
from skills.shanhai import (  # noqa: E402
    FixtureTextBackend,
    ShanHaiLegalTextEvidence,
    TextCitation,
    TextCitationSelector,
    read_text_document,
    resolve_text_citation_across,
)

FIXTURE = PROJECT_ROOT / "fixtures" / "shanhai" / "generated" / "normal.txt"
DUPLICATE_FIXTURE = (
    PROJECT_ROOT / "fixtures" / "shanhai" / "generated" / "duplicate_marker.txt"
)


def main() -> int:
    registry = SourceRegistry()
    registry.register_source("example-maritime-code", label="Synthetic example text")
    artifact = registry.register_artifact(
        "example-maritime-code",
        FIXTURE,
        artifact_id="example-maritime-code",
        media_type="text/plain",
    )

    skill = ShanHaiLegalTextEvidence(FixtureTextBackend())
    result = skill.run(artifact, source_id="example-maritime-code")

    print(f"artifact      : {artifact.artifact_id} ({artifact.content_digest[:24]}...)")
    print(f"skill         : {result.skill_id}")
    print(f"units         : {len(result.units)}")
    print(f"complete      : {result.is_complete_success}")
    print()

    print("evidence units")
    for unit in result.units:
        coordinate = unit.address.context_path[-1]
        print(f"  {unit.unit_id:<44} {unit.unit_class:<10} {coordinate}")
    print()

    document = read_text_document(FIXTURE.read_text(encoding="utf-8"))
    text = document.text

    print("citation: article 3")
    outcome = resolve_text_citation_across(
        result.units, TextCitationSelector(article_number=3), document_text=text
    )
    if isinstance(outcome, TextCitation):
        print(f"  span        : {outcome.span.char_ref} ({outcome.span.byte_ref})")
        print(f"  text        : {outcome.text}")
        print(f"  re-verified : {outcome.verify(text)}")
    else:
        print(f"  refused     : {type(outcome).__name__}: {outcome.message}")
    print()

    print("refusal: a duplicated article marker cannot be cited")
    duplicate_artifact = Artifact.from_file(DUPLICATE_FIXTURE, "example-duplicate")
    duplicate = skill.run(duplicate_artifact, source_id="example-maritime-code")
    duplicate_text = DUPLICATE_FIXTURE.read_text(encoding="utf-8")
    ambiguous = resolve_text_citation_across(
        duplicate.units,
        TextCitationSelector(article_number=2),
        document_text=duplicate_text,
    )
    print(f"  outcome     : {type(ambiguous).__name__}")
    print(f"  candidates  : {len(getattr(ambiguous, 'candidates', ()))}")
    print(f"  message     : {ambiguous.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
