#!/usr/bin/env python3
"""Lexer-level differential test.

For each input, we collect:

  1. The token-span sequence from sqlite's own tokenizer (via the
     `sqlite-tokenize` shim built in Dockerfile.dev).
  2. The leaf-span sequence from our tree-sitter parse tree.

Both are filtered to exclude whitespace / extras, then compared
pairwise on (start_byte, end_byte). Disagreements indicate our
lexical layer has drifted from sqlite's tokenize.c.

This is the lexer-level analogue of the parse-level differential
harness. It catches gaps that the parse-level harness
misses — e.g., we tokenize `0xFF` as one numeric_literal but sqlite
splits as two tokens (or vice versa). The parse may still succeed
but the tree shape differs from sqlite's view of the input.

Usage:
    scripts/lexer-differential-test.py [--max-failures N]
                                       [--inputs FILE]
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent

# TK_* codes from sqlite's parse.h. The full set is dozens of values;
# we only need the ones that should be SKIPPED in the comparison
# (whitespace, illegal). The remaining tokens are compared by span
# alone — we don't try to map TK codes to tree-sitter node types.
SQLITE_TK_SPACE   = 184
SQLITE_TK_ILLEGAL = 185

# Tree-sitter node types to skip in our leaf walk (match sqlite's
# whitespace skip).
EXTRAS = {"line_comment", "block_comment"}


def sqlite_tokens(sql: bytes) -> list[tuple[int, int, int]]:
    """Run the sqlite-tokenize shim. Return list of (offset, length,
    tk_code) excluding whitespace tokens."""
    p = subprocess.run(
        ["sqlite-tokenize"],
        input=sql,
        capture_output=True,
        check=True,
    )
    out: list[tuple[int, int, int]] = []
    for line in p.stdout.decode().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        off, n, tt = int(parts[0]), int(parts[1]), int(parts[2])
        if tt == SQLITE_TK_SPACE:
            continue
        out.append((off, off + n, tt))
    return out


def ts_leaf_spans(parser, sql: bytes) -> list[tuple[int, int, str]]:
    """Walk tree-sitter's tree, return (start, end, type) for every
    leaf (named OR anonymous), excluding extras (comments). Anonymous
    leaves include keyword tokens (`CREATE`, `TABLE`), punctuation
    (`(`, `,`, `;`), and operator strings — these correspond to
    sqlite's TK_* tokens and must be included for the span-level
    comparison to align."""
    tree = parser.parse(sql)
    out: list[tuple[int, int, str]] = []

    def walk(node):
        if node.type in EXTRAS:
            return
        if node.child_count == 0:
            # Skip zero-width leaves (MISSING node placeholders).
            if node.start_byte != node.end_byte:
                out.append((node.start_byte, node.end_byte, node.type))
            return
        for c in node.children:
            walk(c)

    walk(tree.root_node)
    return out


def _has_node(node, types: tuple[str, ...]) -> bool:
    if node.type in types:
        return True
    return any(_has_node(c, types) for c in node.children)


def has_error(node) -> bool:
    if node.type in ("ERROR", "malformed_blob_literal", "malformed_number_id"):
        return True
    if node.is_missing:
        return True
    return any(has_error(c) for c in node.children)


def read_inputs(path: Path) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        if not raw or raw.startswith("#"):
            continue
        out.append(
            raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path,
                    default=REPO_ROOT / "test" / "snapshots" / "inputs.txt")
    ap.add_argument("--max-failures", type=int, default=10)
    args = ap.parse_args()

    inputs = read_inputs(args.inputs)
    if not inputs:
        print(f"error: no inputs at {args.inputs}", file=sys.stderr)
        return 2

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    total = 0
    skipped = 0
    failures: list[tuple[str, str]] = []
    for sql in inputs:
        sql_b = sql.encode("utf-8")
        # Skip inputs sqlite or we reject — comparison is meaningful
        # only for inputs both accept.
        tree = parser.parse(sql_b)
        if has_error(tree.root_node):
            skipped += 1
            continue
        sq = sqlite_tokens(sql_b)
        if not sq:
            skipped += 1
            continue
        # Skip dot-commands (sqlite isn't aware of them — its
        # tokenizer emits `.` + `name` while shell.c handles them at
        # a higher layer) and inputs with vtab module args (we
        # deliberately coalesce into vtab_module_arg for byte-coverage
        # while sqlite tokenizes the inner contents). These are
        # architectural differences, not lexer drift.
        if _has_node(tree.root_node, ("dot_command", "vtab_module_arg")):
            skipped += 1
            continue

        ts = ts_leaf_spans(parser, sql_b)
        # Compare span SETS rather than ordered lists — tree-sitter
        # may walk in a slightly different traversal order than
        # sqlite emits, but the SET of (start,end) spans must agree.
        sq_spans = {(s, e) for (s, e, _) in sq}
        ts_spans = {(s, e) for (s, e, _) in ts}

        only_sqlite = sq_spans - ts_spans
        only_ours = ts_spans - sq_spans

        total += 1
        if only_sqlite or only_ours:
            if len(failures) < args.max_failures:
                msg_parts = []
                if only_sqlite:
                    samples = sorted(only_sqlite)[:3]
                    msg_parts.append(
                        f"sqlite-only spans: {samples}"
                    )
                if only_ours:
                    samples = sorted(only_ours)[:3]
                    msg_parts.append(
                        f"ours-only spans: {samples}"
                    )
                failures.append((sql, "; ".join(msg_parts)))

    print(f"lexer-differential: {total} comparable inputs ({skipped} skipped)")
    print(f"  span disagreements: {len(failures)}")
    for sql, msg in failures[:args.max_failures]:
        one = sql.replace("\n", " ")[:120]
        print(f"  - SQL: {one}")
        print(f"    {msg}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
