#!/usr/bin/env python3
"""Run tree-sitter-sqlite3 against the upstream sqlite test corpus.

Reads SQL fragments from stdin (output of extract-sql-fragments.py),
parses each with our grammar, and reports any fragment that produces
an ERROR or MISSING node.

Exit codes:
    0  -- all fragments parsed cleanly (or only allowlisted ones failed)
    1  -- one or more non-allowlisted fragments failed to parse
    2  -- usage / setup error

Usage:
    scripts/extract-sql-fragments.py vendor/sqlite-test-corpus/test/*.test \\
        | scripts/parse-upstream-corpus.py [--max-failures N] [--allowlist PATH]

The allowlist file lists fragment-source-locations (file:line) that are
known-failing for documented reasons. Format: one location per line,
with optional '#' comments and rationale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(
        f"error: missing python deps ({e}). Install with:\n"
        "    pip install tree-sitter\n"
        "    pip install -e .   # builds the tree_sitter_sqlite3 binding\n",
        file=sys.stderr,
    )
    sys.exit(2)


_MALFORMED_TYPES = {"malformed_blob_literal", "malformed_number_id"}


def has_error_or_missing(node: "tree_sitter.Node") -> tuple[bool, str | None]:
    """Walk the tree; return (failed, first-failure-description)."""
    if node.type == "ERROR":
        return True, f"ERROR at {node.start_point}-{node.end_point}"
    if node.is_missing:
        return True, f"MISSING {node.type!r} at {node.start_point}"
    if node.type in _MALFORMED_TYPES:
        return True, f"{node.type} at {node.start_point}-{node.end_point}"
    for child in node.children:
        failed, desc = has_error_or_missing(child)
        if failed:
            return True, desc
    return False, None


def load_allowlist(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    out = set()
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def parse_fragments(
    fragments: Iterable[tuple[str, str]],
    parser: "tree_sitter.Parser",
    allowlist: set[str],
    max_failures: int,
) -> tuple[int, int, int, list[tuple[str, str, str]]]:
    """Parse each fragment, return (total, passed, allowlisted, failures)."""
    total = 0
    passed = 0
    allowlisted = 0
    failures: list[tuple[str, str, str]] = []

    for loc, sql in fragments:
        total += 1
        tree = parser.parse(sql.encode("utf-8"))
        failed, desc = has_error_or_missing(tree.root_node)
        if not failed:
            passed += 1
            continue
        if loc in allowlist:
            allowlisted += 1
            continue
        if len(failures) < max_failures:
            failures.append((loc, sql, desc or "<unknown>"))

    return total, passed, allowlisted, failures


def read_stdin_fragments() -> Iterable[tuple[str, str]]:
    """Parse the line-oriented format produced by extract-sql-fragments.py."""
    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        if not raw or raw.startswith("#"):
            continue
        loc, _, escaped = raw.partition("\t")
        if not escaped:
            continue
        # Reverse the escaping done in extract-sql-fragments.py.
        sql = escaped.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        yield loc, sql


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--max-failures",
        type=int,
        default=20,
        help="stop collecting failure samples after N (default: 20)",
    )
    ap.add_argument(
        "--allowlist",
        type=Path,
        default=Path("test/upstream-corpus-allowlist.txt"),
        help="path to allowlist file (default: test/upstream-corpus-allowlist.txt)",
    )
    ap.add_argument(
        "--summary-only",
        action="store_true",
        help="suppress per-failure detail; print only counts",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=(
            "pass rate (0.0-1.0) below which to exit non-zero. "
            "If unset, any failure exits non-zero. Used to lock in a "
            "regression floor while the long tail is being closed."
        ),
    )
    args = ap.parse_args()

    allowlist = load_allowlist(args.allowlist)

    language = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(language)

    total, passed, allowlisted, failures = parse_fragments(
        read_stdin_fragments(), parser, allowlist, args.max_failures
    )

    failed = total - passed - allowlisted
    print(f"upstream-corpus: {total} fragments")
    print(f"  passed:      {passed} ({100*passed/total:.1f}%)" if total else "  passed: 0")
    print(f"  allowlisted: {allowlisted}")
    print(f"  FAILED:      {failed}")

    if failures and not args.summary_only:
        print("\nFirst failures (capped):")
        for loc, sql, desc in failures:
            sql_one_line = sql.replace("\n", " ")[:120]
            print(f"  {loc}  {desc}")
            print(f"    SQL: {sql_one_line}")

    if failed == 0:
        return 0
    if args.threshold is not None and total > 0:
        rate = (passed + allowlisted) / total
        if rate >= args.threshold:
            print(
                f"\npass rate {rate:.4f} >= threshold {args.threshold:.4f}; "
                "OK (regression floor met).",
            )
            return 0
        print(
            f"\npass rate {rate:.4f} < threshold {args.threshold:.4f}; "
            "REGRESSION.",
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
