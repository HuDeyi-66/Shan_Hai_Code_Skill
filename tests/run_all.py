"""ShanHai Skill test runner.

    python tests/run_all.py --core-root <seaflow-root> [--quiet]

SeaFlow Core is required and must be supplied explicitly, either as
``--core-root`` or through the ``SEAFLOW_CORE_ROOT`` environment variable. Core
is not vendored into this repository. There is no sibling-directory fallback.

The optional ``python-calamine`` binding belongs to LuoHai, not to ShanHai; the
stored constants are inert here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ShanHai Skill test suite")
    parser.add_argument(
        "--core-root",
        default=None,
        help="directory containing core/ (a SeaFlow checkout root or a staged Core root)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="one line per module instead of per test",
    )
    args = parser.parse_args(argv)

    # The bootstrap validates Core at import time, so the explicit root has to
    # be in the environment before it is imported.
    if args.core_root:
        os.environ["SEAFLOW_CORE_ROOT"] = str(Path(args.core_root).resolve())

    import _bootstrap  # noqa: E402  (path bootstrap; validates Core)

    print(f"[runner] SeaFlow Core root: {_bootstrap.CORE_ROOT}")

    loader = unittest.TestLoader()
    suite = loader.discover(str(TESTS_DIR), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)

    summary = {
        "ran": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "ok": result.wasSuccessful(),
    }
    print("RUN_ALL_SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
