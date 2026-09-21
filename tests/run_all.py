"""ShanHai test runner.

    python tests/run_all.py [--quiet]

No runtime, service or sibling checkout is required. ShanHai is standalone: the
suite runs against this repository alone.
"""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ShanHai Skill test suite")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="one line per module instead of per test",
    )
    args = parser.parse_args(argv)

    import _bootstrap  # noqa: E402  (path bootstrap)

    print("[runner] standalone: no runtime or external checkout required")
    print(f"[runner] repository root: {_bootstrap.PROJECT_ROOT}")

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
