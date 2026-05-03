#!/usr/bin/env python3
"""Production-level coverage for the tree-sitter-sqlite3 grammar.

Parses the union of:
  - hand-written corpus fixtures under test/corpus/*.txt
  - the upstream sqlite test corpus (extracted via
    scripts/extract-sql-fragments.py)
through our grammar, walks every produced tree, and tallies which
named node types appeared. Compares to the universe of named types
declared in src/node-types.json and reports the coverage ratio plus
the names of unhit types.

This is the closest equivalent to "MC/DC for a tree-sitter grammar"
we can get without custom instrumentation. Every tree-sitter rule
that produces a visible node corresponds to a parse.y nonterminal
or an alternative we explicitly named via alias(); if a type is
never hit by ANY input across our combined corpus, that rule is
either unreachable, dead code, or — most often — exercising a
construct we forgot to add a fixture for.

Exit codes:
  0  -- coverage at or above the configured threshold
  1  -- coverage below threshold
  2  -- usage / setup error

Usage:
    scripts/grammar-coverage.py [--threshold 0.92] [--corpus FILE]...

If no --corpus is given, reads SQL fragments from stdin (the format
produced by extract-sql-fragments.py).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Iterator

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent


def all_named_types(node_types_path: Path) -> set[str]:
    """All named node types declared by the generated grammar.

    Excludes:
      - anonymous tokens (`named: false`)
      - the synthetic ERROR / MISSING types tree-sitter inserts for
        recovery (those should never be in healthy parses)
      - hidden rules (`_`-prefixed names) — they don't produce visible
        nodes; their alternatives surface under the parent's type
    """
    data = json.loads(node_types_path.read_text())
    out: set[str] = set()
    for entry in data:
        t = entry.get("type")
        if not entry.get("named"):
            continue
        if not t or t.startswith("_") or t == "ERROR":
            continue
        out.add(t)
    return out


def collect_types(node, observed: set[str]) -> None:
    if node.is_named:
        observed.add(node.type)
    for c in node.children:
        collect_types(c, observed)


def iter_corpus_fragments(corpus_files: list[Path]) -> Iterator[str]:
    """Extract the SQL between `===...` headers in test/corpus/*.txt
    fixture files. Format:

        ===========
        test name
        ===========

        SQL...

        ---

        (sexp...)
    """
    sep = re.compile(r"^={3,}$", re.MULTILINE)
    boundary = re.compile(r"^---+$", re.MULTILINE)
    for path in corpus_files:
        text = path.read_text()
        # Split into test sections by the `===` headers.
        # Each section: after the second `===` line, the SQL runs until
        # the `---` boundary.
        chunks = sep.split(text)
        # chunks[0] is preamble; pairs of (title, body...) follow.
        i = 1
        while i < len(chunks):
            # title chunk + body chunk; we want the body after the
            # closing === which is part of the NEXT chunk's start.
            body = chunks[i + 1] if i + 1 < len(chunks) else ""
            m = boundary.search(body)
            sql = body[: m.start()] if m else body
            sql = sql.strip()
            if sql:
                yield sql
            i += 2


def iter_stdin_fragments() -> Iterator[str]:
    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        if not raw or raw.startswith("#"):
            continue
        _, _, escaped = raw.partition("\t")
        if not escaped:
            continue
        yield (
            escaped.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="coverage floor (0.0-1.0); below this exits non-zero",
    )
    ap.add_argument(
        "--include-handwritten-corpus",
        action="store_true",
        default=True,
        help="include test/corpus/*.txt fixtures (default: on)",
    )
    ap.add_argument(
        "--list-unhit",
        action="store_true",
        help="print every unhit type, not just the first 30",
    )
    args = ap.parse_args()

    node_types = all_named_types(REPO_ROOT / "src" / "node-types.json")

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    observed: set[str] = set()
    parsed = 0

    if args.include_handwritten_corpus:
        corpus_dir = REPO_ROOT / "test" / "corpus"
        for sql in iter_corpus_fragments(sorted(corpus_dir.glob("*.txt"))):
            tree = parser.parse(sql.encode("utf-8"))
            collect_types(tree.root_node, observed)
            parsed += 1

    if not sys.stdin.isatty():
        for sql in iter_stdin_fragments():
            tree = parser.parse(sql.encode("utf-8"))
            collect_types(tree.root_node, observed)
            parsed += 1

    hit = observed & node_types
    unhit = node_types - observed
    rate = len(hit) / len(node_types) if node_types else 1.0

    print(f"grammar coverage: {len(hit)}/{len(node_types)} types hit ({rate:.1%})")
    print(f"  parsed inputs:  {parsed}")
    print(f"  unhit:          {len(unhit)}")

    if unhit:
        cap = None if args.list_unhit else 30
        print("\nUnhit named types:")
        for t in sorted(unhit)[:cap]:
            print(f"  {t}")
        if cap is not None and len(unhit) > cap:
            print(f"  ... and {len(unhit) - cap} more (use --list-unhit)")

    if args.threshold is not None and rate < args.threshold:
        print(f"\ncoverage {rate:.4f} < threshold {args.threshold:.4f}; FAIL")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
