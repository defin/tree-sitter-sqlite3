#!/usr/bin/env python3
"""Mechanical keyword-fallback coverage matrix.

Reads parse.y's `%fallback ID ...` declarations and emits, for each
keyword in the fallback list:

  - a column-name test:        CREATE TABLE t(<KEYWORD> INT);
  - a table-name test:         SELECT * FROM <KEYWORD>;
  - an alias test:             SELECT 1 AS <KEYWORD>;
  - a CTE-name test:           WITH <KEYWORD> AS (SELECT 1) SELECT * FROM <KEYWORD>;

Each variant is parsed; the run fails if any produces an ERROR /
MISSING node. This catches regressions where a keyword we thought
was fallback-eligible has slipped out of `_id`'s choice set.

This script is BOTH a CI harness AND a test generator: run it
periodically to refresh the matrix when sqlite ships new fallback
keywords. The keyword list is extracted from `vendor/parse.y` so the
test corpus follows the upstream pin automatically.

Usage:
    scripts/gen-fallback-tests.py [--list] [--max-failures N]
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
PARSE_Y = REPO_ROOT / "vendor" / "parse.y"


def extract_fallback_keywords(parse_y: Path) -> list[str]:
    """Pull the `%fallback ID <kw> <kw> ...` block from parse.y.

    Returns the list of keywords (lowercased) that fall back to ID,
    excluding ifdef-gated subsets that don't apply to a default build.
    """
    text = parse_y.read_text()
    # The fallback block runs from `%fallback ID` to a `.` on its own.
    m = re.search(r"%fallback\s+ID\b(.+?)\.", text, re.DOTALL)
    if not m:
        raise RuntimeError("no %fallback ID block in parse.y")
    body = m.group(1)
    body = re.sub(r"//[^\n]*", "", body)
    # parse.y uses %ifdef/%ifndef to gate fallbacks on compile flags.
    # The standard sqlite build defines NO OMIT_* flags and NO
    # ENABLE_* flags (except those baked into the amalgamation), so:
    #   %ifdef SQLITE_OMIT_X   -> tokens NOT in fallback
    #   %ifdef SQLITE_ENABLE_X -> tokens NOT in fallback
    #   %ifndef SQLITE_OMIT_X  -> tokens IN fallback
    # Strip the %ifdef blocks entirely (their tokens are NOT included
    # in the standard build's fallback set), keep %ifndef contents.
    body = re.sub(
        r"%ifdef\s+\S+\n.*?%endif\s+\S+",
        "",
        body,
        flags=re.DOTALL,
    )
    body = re.sub(r"%ifndef\s+\S+\n", "", body)
    body = re.sub(r"%endif\s+\S+", "", body)
    # Special tokens we should NOT test as identifiers — they're
    # parse.y aliases for compound keywords or have other constraints.
    skip = {
        "like_kw",       # parse.y class for LIKE/GLOB/REGEXP/MATCH
        "ctime_kw",      # CURRENT_DATE/TIME/TIMESTAMP class
        "join_kw",       # CROSS/FULL/INNER/LEFT/NATURAL/OUTER/RIGHT
        "columnkw",      # COLUMN keyword, parse.y-internal alias
    }
    out: list[str] = []
    for tok in re.findall(r"\b[A-Z_]+\b", body):
        kw = tok.lower()
        if kw in skip:
            continue
        if kw in out:
            continue
        out.append(kw)
    return out


def has_error(node) -> bool:
    if node.type in ("ERROR", "malformed_blob_literal", "malformed_number_id"):
        return True
    if node.is_missing:
        return True
    return any(has_error(c) for c in node.children)


def variants(kw: str) -> list[tuple[str, str]]:
    """Return (label, sql) variants exercising kw in identifier position."""
    return [
        ("col-name",   f"CREATE TABLE t({kw} INT);"),
        ("table-name", f"SELECT * FROM {kw};"),
        ("alias",      f"SELECT 1 AS {kw};"),
        ("cte-name",   f"WITH {kw} AS (SELECT 1) SELECT * FROM {kw};"),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true",
                    help="just print the extracted fallback keyword list")
    ap.add_argument("--max-failures", type=int, default=20)
    args = ap.parse_args()

    keywords = extract_fallback_keywords(PARSE_Y)
    print(f"# {len(keywords)} fallback keywords extracted from {PARSE_Y.relative_to(REPO_ROOT)}")
    if args.list:
        for kw in keywords:
            print(kw)
        return 0

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    total = 0
    failures: list[tuple[str, str, str]] = []
    for kw in keywords:
        for label, sql in variants(kw):
            total += 1
            tree = parser.parse(sql.encode("utf-8"))
            if has_error(tree.root_node):
                if len(failures) < args.max_failures:
                    failures.append((kw, label, sql))

    print(f"fallback-matrix: {total} variants ({len(keywords)} keywords × 4 positions)")
    print(f"  failures: {len(failures)}")
    for kw, label, sql in failures:
        print(f"  - [{label:10}] {kw}: {sql}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
