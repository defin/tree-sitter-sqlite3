#!/usr/bin/env python3
"""Error-recovery quality tests.

For an IDE / linter consuming the parse tree, the QUALITY of recovery
on malformed input matters as much as success on well-formed input.
A grammar that produces (ERROR) covering the entire statement is
useless for highlighting — we want recovery to localize errors to the
malformed REGION while keeping the surrounding shape intact.

This harness defines a curated set of malformed-input fixtures, each
with assertions on the resulting tree:

  - the parse must not crash,
  - at least one ERROR / MISSING / malformed_* node must surface,
  - the ERROR region must be SMALLER than the entire statement
    (specifically, the well-formed prefix and suffix should still
    parse to recognisable named nodes).

Usage:
    scripts/error-recovery-test.py
"""

from __future__ import annotations
import sys
from dataclasses import dataclass

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


@dataclass
class Case:
    name: str
    sql: str
    # We expect AT LEAST these named-node types to survive recovery
    # (the well-formed parts should still be there).
    expect_survives: tuple[str, ...] = ()
    # We expect at least one diagnostic node (ERROR / MISSING /
    # malformed_*) somewhere in the tree.
    expect_diagnostic: bool = True
    # If set, the ERROR region must be smaller than this (in bytes).
    # Catches "whole statement collapses to ERROR" failure mode.
    max_error_span_bytes: int | None = None


CASES: list[Case] = [
    # Missing comma between columns.
    Case(
        name="missing-comma-between-columns",
        sql="SELECT a b FROM t1;",
        expect_survives=("select_statement", "from_clause", "qualified_table_name"),
        # Without comma, parser tries to interpret `b` as alias, so
        # this may parse cleanly. Expect_diagnostic=False here.
        expect_diagnostic=False,
    ),
    # Unclosed paren.
    Case(
        name="unclosed-paren-in-where",
        sql="SELECT * FROM t1 WHERE (a > 5;",
        expect_survives=("select_statement", "from_clause"),
    ),
    # Typo'd keyword.
    Case(
        name="typo-keyword-WHEREwww",
        sql="UPDATE t1 SET a=0 WHEREwww b=1;",
        expect_survives=("update_statement",),
    ),
    # Trailing garbage after a complete statement.
    Case(
        name="trailing-garbage-after-statement",
        sql="SELECT 1; @@@invalid@@@",
        expect_survives=("select_statement",),
    ),
    # Garbage in the middle of a multi-statement list.
    Case(
        name="garbage-between-statements",
        sql="SELECT 1; %%%bogus%%% SELECT 2;",
        expect_survives=("select_statement",),
    ),
    # Missing FROM.
    Case(
        name="select-from-nothing",
        sql="SELECT * FROM;",
        expect_survives=("select_statement",),
    ),
    # Unclosed string literal mid-statement. Severe truncation —
    # tree-sitter collapses to ERROR; we just check it doesn't crash
    # and produces a diagnostic.
    Case(
        name="unclosed-string-literal",
        sql="INSERT INTO t1 VALUES('open never closed",
        expect_survives=(),  # too truncated to recover statement shape
    ),
    # Half-typed CREATE TABLE — severe truncation, see above.
    Case(
        name="half-typed-create-table",
        sql="CREATE TABLE t1 (",
        expect_survives=(),
    ),
    # Less-severe partial input: half-typed but with a closing token.
    # Tree-sitter SHOULD recover the outer shape here.
    Case(
        name="partial-create-table-with-paren-close",
        sql="CREATE TABLE t1 (a, );",
        expect_survives=("create_table_statement",),
    ),
    # Malformed blob in expression — external scanner should localize.
    Case(
        name="malformed-blob-in-select",
        sql="SELECT X'01001' FROM t1;",
        expect_survives=("select_statement", "from_clause"),
        max_error_span_bytes=15,  # the bad blob span only
    ),
    # Number-fused-to-id — same.
    Case(
        name="malformed-number-id-in-select",
        sql="SELECT 123abc FROM t1;",
        expect_survives=("select_statement", "from_clause"),
        max_error_span_bytes=15,
    ),
]


def collect_diagnostics(node, out: list) -> None:
    if node.type in ("ERROR", "malformed_blob_literal", "malformed_number_id"):
        out.append(node)
    if node.is_missing:
        out.append(node)
    for c in node.children:
        collect_diagnostics(c, out)


def collect_named_types(node, out: set) -> None:
    if node.is_named:
        out.add(node.type)
    for c in node.children:
        collect_named_types(c, out)


def main() -> int:
    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    failures: list[tuple[str, str]] = []
    for case in CASES:
        tree = parser.parse(case.sql.encode("utf-8"))
        types_seen: set[str] = set()
        collect_named_types(tree.root_node, types_seen)
        diagnostics: list = []
        collect_diagnostics(tree.root_node, diagnostics)

        # Check expected survival.
        for required in case.expect_survives:
            if required not in types_seen:
                failures.append((
                    case.name,
                    f"expected {required!r} in tree, got: {sorted(types_seen)}",
                ))

        # Check diagnostic presence.
        if case.expect_diagnostic and not diagnostics:
            failures.append((
                case.name,
                "expected at least one ERROR / MISSING / malformed_* node, got none",
            ))

        # Check error-span size.
        if case.max_error_span_bytes is not None and diagnostics:
            biggest = max(d.end_byte - d.start_byte for d in diagnostics)
            if biggest > case.max_error_span_bytes:
                failures.append((
                    case.name,
                    f"largest diagnostic span = {biggest} bytes, "
                    f"max allowed = {case.max_error_span_bytes}",
                ))

    print(f"error-recovery: {len(CASES)} cases checked")
    print(f"  failures: {len(failures)}")
    for name, msg in failures:
        print(f"  - {name}: {msg}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
