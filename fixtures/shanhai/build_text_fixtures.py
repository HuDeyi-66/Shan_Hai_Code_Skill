"""V2.3 -- ShanHai text fixtures and their truth manifests.

Run directly to (re)generate::

    python fixtures/shanhai/build_text_fixtures.py

Every fixture is written byte-deterministically (UTF-8, LF newlines, no BOM), so
a rebuild is byte-identical. The truth manifest for the *normal* fixture records
the exact character span of every provision, which is what the citation tests
assert against -- a citation that does not reproduce those offsets is wrong.

Fixture cases, one per structural condition the Skill must keep distinct:

=========================  ==================================================
``normal``                 chapter + articles + paragraphs; parses fully
``empty``                  zero bytes: must be a failure, never "validated"
``missing_marker``         a marker is present but its numeral is unresolvable
``numbering_gap_no_marker`` articles 1 and 3 with nothing marker-shaped between
``malformed_marker``       a marker-shaped line that is not a well-formed marker
``duplicate_marker``       the same article number twice
``gap``                    articles 1, 2, 5: a clean numbering gap
``unsupported_structure``  prose / markdown with no legal markers
``latin_headings``         "Article N" headings, outside this Skill's scope
``not_utf8``               invalid UTF-8 bytes: an encoding failure
=========================  ==================================================

NOTE: this file contains non-ASCII text on purpose. Do not rewrite it with a
shell ``Get-Content``/``Set-Content`` round trip, which can mangle the encoding
and silently corrupt the fixtures.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

#: Article marker pattern, duplicated here on purpose. The truth manifest must be
#: derived independently of the code it is used to check; importing the Skill's
#: own regex would let a parser bug rewrite its own expected answer.
#:
#: The numeral alternation is numeric-first and the CJK class contains only digit
#: characters, so ``第二章`` can never match here: an article marker is
#: ``第<digits>条`` and nothing else.
ARTICLE_MARKER = re.compile(
    r"^\s*(第\s*([0-9]+|[〇零一二三四五六七八九十百千]+)\s*条)"
)

#: Chapter marker pattern. A chapter heading *ends* the preceding article, so the
#: truth builder must treat it as a boundary. Ignoring chapters here once put
#: ``第二章 船舶`` inside article 2's extent, which disagreed with the parser and
#: with the artifact's real structure.
CHAPTER_MARKER = re.compile(
    r"^\s*(第\s*([0-9]+|[〇零一二三四五六七八九十百千]+)\s*章)"
)

ROOT = Path(__file__).resolve().parent
GENERATED_DIR = ROOT / "generated"
TRUTH_DIR = ROOT / "truth"

#: Repository root, derived from this file's location (fixtures/shanhai/...).
REPOSITORY_ROOT = ROOT.parent.parent


def _repository_relative(path: Path) -> str:
    """A path relative to the repository root, with forward slashes.

    The case manifest is committed, so it must not contain a checkout-specific
    absolute path: that would leak the publisher's local layout and would change
    whenever somebody clones the repository elsewhere. The fixture bytes and the
    truth manifest are unaffected.
    """
    try:
        relative = path.resolve().relative_to(REPOSITORY_ROOT.resolve())
    except ValueError:
        relative = path
    return relative.as_posix()

_CASES_NAME = "cases.json"
_NORMAL_TRUTH_NAME = "normal_truth.json"

#: The normal fixture, as an explicit line list. Written this way rather than as
#: one triple-quoted block so the exact line structure is visible and every
#: offset in the truth manifest is auditable by eye.
NORMAL_LINES: tuple[str, ...] = (
    "中华人民共和国海商法（节选）",
    "",
    "第一章 总则",
    "",
    "第一条 为了调整海上运输关系、船舶关系，维护当事人各方的合法权益，",
    "促进海上运输和经济贸易的发展，制定本法。",
    "",
    "第二条 本法所称海上运输，是指海上货物运输和海上旅客运输，",
    "包括海江之间、江海之间的直达运输。",
    "本法第四章海上货物运输合同的规定，不适用于中华人民共和国港口之间的海上货物运输。",
    "",
    "第二章 船舶",
    "",
    "第三条 本法所称船舶，是指海船和其他海上移动式装置，",
    "但是用于军事的、政府公务的船舶和二十总吨以下的小型船艇除外。",
    "",
    "前款所称船舶，包括船舶属具。",
    "",
    "第四条 船舶经依法登记，取得中华人民共和国国籍。",
    "",
    "第五条 船舶所有权的取得、转让和消灭，应当向船舶登记机关登记。",
    "",
)

MISSING_MARKER_LINES: tuple[str, ...] = (
    "测试法规",
    "",
    "第一条 第一条内容。",
    "",
    "第廿条 此条使用了本读取器不支持的数词形式。",
    "",
    "第二十一条 第二十一条内容。",
    "",
)

NUMBERING_GAP_NO_MARKER_LINES: tuple[str, ...] = (
    "测试法规",
    "",
    "第一条 第一条内容。",
    "",
    "第三条 第三条内容。",
    "",
)

MALFORMED_MARKER_LINES: tuple[str, ...] = (
    "测试法规",
    "",
    "第一条 第一条内容。",
    "",
    "第条 这是一个无法解析的标记。",
    "",
    "第三条 第三条内容。",
    "",
)

DUPLICATE_MARKER_LINES: tuple[str, ...] = (
    "测试法规",
    "",
    "第一条 第一条内容。",
    "",
    "第二条 第二条内容（第一次出现）。",
    "",
    "第二条 第二条内容（第二次出现）。",
    "",
    "第三条 第三条内容。",
    "",
)

GAP_LINES: tuple[str, ...] = (
    "测试法规",
    "",
    "第一条 第一条内容。",
    "",
    "第二条 第二条内容。",
    "",
    "第五条 第五条内容。",
    "",
)

UNSUPPORTED_LINES: tuple[str, ...] = (
    "# 会议记录",
    "",
    "本文件记录了关于海上货物运输的讨论要点。",
    "与会各方就承运人责任限制交换了意见，未形成结论。",
    "",
    "- 责任限制需要进一步研究",
    "- 下一次会议讨论赔偿标准",
    "",
)

LATIN_HEADINGS_LINES: tuple[str, ...] = (
    "Maritime Code (Excerpt)",
    "",
    "Article 1",
    "This Code governs maritime transport relations.",
    "",
    "Article 2",
    "For the purposes of this Code, vessel means a seagoing ship.",
    "",
)


def _text_of(lines: tuple[str, ...]) -> str:
    return "\n".join(lines) + "\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fixture_bytes(case: str) -> bytes:
    """The exact bytes of one fixture case."""
    if case == "normal":
        return _text_of(NORMAL_LINES).encode("utf-8")
    if case == "empty":
        return b""
    if case == "missing_marker":
        return _text_of(MISSING_MARKER_LINES).encode("utf-8")
    if case == "numbering_gap_no_marker":
        return _text_of(NUMBERING_GAP_NO_MARKER_LINES).encode("utf-8")
    if case == "malformed_marker":
        return _text_of(MALFORMED_MARKER_LINES).encode("utf-8")
    if case == "duplicate_marker":
        return _text_of(DUPLICATE_MARKER_LINES).encode("utf-8")
    if case == "gap":
        return _text_of(GAP_LINES).encode("utf-8")
    if case == "unsupported_structure":
        return _text_of(UNSUPPORTED_LINES).encode("utf-8")
    if case == "latin_headings":
        return _text_of(LATIN_HEADINGS_LINES).encode("utf-8")
    if case == "not_utf8":
        # 0xFF is never valid UTF-8. Deliberately not a BOM and not a plausible
        # legacy encoding: the point is that the reader refuses rather than
        # guessing.
        return "测试".encode("utf-16-le") + b"\xff\xfe"
    raise KeyError(f"unknown fixture case: {case!r}")


#: Every case with the condition it is built to provoke. The expectation text is
#: the contract the tests assert.
CASES: dict[str, dict[str, Any]] = {
    "normal": {
        "file": "normal.txt",
        "condition": "none",
        "expectation": "chapters and articles are detected; articles carry exact "
                       "character spans and paragraph splits",
    },
    "empty": {
        "file": "empty.txt",
        "condition": "empty_artifact",
        "expectation": "one container unit, loss 'empty', parsed=False; never a "
                       "success and never 'validated'",
    },
    "missing_marker": {
        "file": "missing_marker.txt",
        "condition": "missing_marker",
        "expectation": "a marker is present but its numeral is unresolvable; "
                       "reported as missing_marker -- the marker's own text is "
                       "read, and this is NOT reported as numbering_gap",
    },
    "numbering_gap_no_marker": {
        "file": "numbering_gap_no_marker.txt",
        "condition": "numbering_gap",
        "expectation": "articles 1 and 3 with nothing marker-shaped between them: "
                       "the expected article 2 is genuinely absent, reported as "
                       "numbering_gap and NOT as missing_marker",
    },
    "malformed_marker": {
        "file": "malformed_marker.txt",
        "condition": "malformed_marker",
        "expectation": "the malformed marker is reported as malformed_marker, NOT "
                       "as a numbering gap, and is not emitted as a citable article",
    },
    "duplicate_marker": {
        "file": "duplicate_marker.txt",
        "condition": "duplicate_marker",
        "expectation": "both article 2 occurrences produce units; a citation to "
                       "article 2 returns ambiguous listing both",
    },
    "gap": {
        "file": "gap.txt",
        "condition": "numbering_gap",
        "expectation": "articles 1, 2 and 5 detected; numbering_gap reported for "
                       "3 and 4, which are absent",
    },
    "unsupported_structure": {
        "file": "unsupported_structure.txt",
        "condition": "unsupported_structure",
        "expectation": "no provisions; one container unit with loss 'unsupported'",
    },
    "latin_headings": {
        "file": "latin_headings.txt",
        "condition": "unsupported_structure",
        "expectation": "Latin 'Article N' headings are refused as unsupported "
                       "rather than half-parsed",
    },
    "not_utf8": {
        "file": "not_utf8.txt",
        "condition": "encoding_failure",
        "expectation": "decode failure is fatal and reported; the bytes are not "
                       "lossily decoded",
    },
}


def case_path(case: str) -> Path:
    return GENERATED_DIR / CASES[case]["file"]


def _normal_truth(text: str) -> dict[str, Any]:
    """Compute the exact span of every provision in the normal fixture.

    Recomputed from the bytes on every build rather than hand-maintained, so the
    manifest cannot drift from the artifact.

    An article runs from its marker line to just before the next *structural*
    line -- the next article marker **or the next chapter heading** -- with
    trailing blank lines excluded. Treating a chapter heading as a boundary
    matters: without it, ``第二章 船舶`` lands inside the preceding article's
    extent.
    """
    lines = text.split("\n")
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line) + 1

    marker_lines = [
        index for index, line in enumerate(lines) if ARTICLE_MARKER.match(line)
    ]
    boundary_lines = [
        index
        for index, line in enumerate(lines)
        if ARTICLE_MARKER.match(line) or CHAPTER_MARKER.match(line)
    ]

    provisions: list[dict[str, Any]] = []
    for index, start_line in enumerate(marker_lines):
        following = [b for b in boundary_lines if b > start_line]
        if following:
            end_line = following[0] - 1
        else:
            end_line = len(lines) - 1
        # Trim trailing blank lines: they separate structural elements, they are
        # not part of either one.
        while end_line > start_line and not lines[end_line].strip():
            end_line -= 1

        char_start = offsets[start_line]
        text_block = "\n".join(lines[start_line : end_line + 1])
        char_end = char_start + len(text_block)
        match = ARTICLE_MARKER.match(lines[start_line])
        provisions.append(
            {
                "number": index + 1,
                "marker": match.group(1).strip() if match else "",
                "char_start": char_start,
                "char_end": char_end,
                "line_start": start_line + 1,
                "line_end": end_line + 1,
                "text": text_block,
                "text_length": len(text_block),
            }
        )

    return {
        "schema_version": "seaflow-v2.3-shanhai-truth/v1",
        "fixture": CASES["normal"]["file"],
        "title": lines[0],
        "chapter_count": 2,
        "article_numbers": [p["number"] for p in provisions],
        "articles": provisions,
        "expected_citations": {
            "article_1": {"number": 1, "ref": "第一条"},
            "article_5": {"number": 5, "ref": "第五条"},
            "chapter_2_article_3": {"chapter": 2, "number": 3},
        },
    }


def build_cases_manifest() -> dict[str, Any]:
    files: dict[str, Any] = {}
    for case, spec in CASES.items():
        payload = fixture_bytes(case)
        files[case] = {
            "file": spec["file"],
            "condition": spec["condition"],
            "expectation": spec["expectation"],
            "sha256": _sha256(payload),
            "bytes": len(payload),
        }
    return {
        "schema_version": "seaflow-shanhai-fixture-manifest/v1",
        "component": "shanhai",
        "fixture_root": _repository_relative(GENERATED_DIR),
        "determinism": {
            "encoding": "utf-8",
            "newlines": "lf",
            "bom": False,
            "expected_byte_identical_rebuild": True,
        },
        "cases": files,
        "truth": _NORMAL_TRUTH_NAME,
        "generated_by": "fixtures/shanhai/build_text_fixtures.py",
    }


def write_fixtures(
    out_dir: Path | None = None, truth_dir: Path | None = None
) -> dict[str, Any]:
    out_dir = Path(out_dir or GENERATED_DIR)
    truth_dir = Path(truth_dir or TRUTH_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    for case, spec in CASES.items():
        (out_dir / spec["file"]).write_bytes(fixture_bytes(case))

    manifest = build_cases_manifest()
    (out_dir / _CASES_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
)

    normal_text = _text_of(NORMAL_LINES)
    truth = _normal_truth(normal_text)
    truth["fixture_sha256"] = _sha256(normal_text.encode("utf-8"))
    (truth_dir / _NORMAL_TRUTH_NAME).write_text(
        json.dumps(truth, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
)
    return manifest


def main() -> int:
    manifest = write_fixtures()
    for case, spec in sorted(manifest["cases"].items()):
        print(f"  {case:<22} {spec['sha256'][:16]}  {spec['bytes']:>5} bytes")
    print(f"written to {GENERATED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
