"""ShanHai test bootstrap.

Makes this repository's root importable as ``skills`` and ``fixtures`` when the
suite is run from anywhere, without requiring an install.

There is nothing else to locate. ShanHai is an independent component: it does
not need a runtime, a service, a sibling checkout, or a path supplied from
outside this repository. Earlier revisions of this file resolved a shared Core
root from an environment variable; that requirement is gone, because ShanHai now
carries its own contract in ``skills/shanhai/contracts.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

#: ShanHai-owned fixture locations.
FIXTURE_DIR = PROJECT_ROOT / "fixtures" / "shanhai" / "generated"
TRUTH_DIR = PROJECT_ROOT / "fixtures" / "shanhai" / "truth"
FIXTURE_PATH = FIXTURE_DIR / "normal.txt"
MANIFEST_PATH = FIXTURE_DIR / "cases.json"
TRUTH_PATH = TRUTH_DIR / "normal_truth.json"

#: Scratch directory for the few tests that must write bytes to disk. Created
#: once and reused; a freshly created directory per test is avoided on purpose
#: because some sandboxed Windows setups make a new directory unwritable by the
#: same process, turning cleanup into a spurious failure.
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def artifacts_dir() -> Path:
    """Return the scratch directory, creating it if needed."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


def repository_has_no_private_runtime_dependency() -> bool:
    """True when no module in this repository imports ``core`` or ``app``.

    The source is parsed rather than imported, so the check cannot pass merely
    because an import happened to resolve against something outside the clone.
    """
    import ast

    for path in sorted((PROJECT_ROOT / "skills").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name.split(".")[0] in ("core", "app") for a in node.names):
                    return False
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                if (node.module or "").split(".")[0] in ("core", "app"):
                    return False
    return True
