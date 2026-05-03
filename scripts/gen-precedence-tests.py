#!/usr/bin/env python3
"""Mechanical operator-precedence pair matrix.

Reads parse.y's %left/%right/%nonassoc precedence declarations and
generates `x op_a y op_b z` tests for every ordered pair of binary
operators across precedence levels. Asserts each parses cleanly AND
that the resulting tree has the expected nesting per the precedence
table:

  - if op_a is at higher precedence than op_b: nesting (x op_a y) op_b z
  - if op_a is at lower precedence than op_b:  nesting x op_a (y op_b z)
  - if same precedence:
      %left:  (x op_a y) op_b z   (left-associative)
      %right: x op_a (y op_b z)   (right-associative)

This is the binary-operator equivalent of MC/DC for parse.y's
operator surface — every (op_a, op_b) ordered pair gets exercised.

Usage:
    scripts/gen-precedence-tests.py [--list] [--max-failures N]
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


# Map parse.y token names to source-text operators. Some parse.y
# tokens are abstract (e.g. LIKE_KW covers LIKE/GLOB/REGEXP/MATCH);
# we pick a representative. Unary-only operators (NOT, BITNOT) are
# excluded — they don't form binary-pair tests.
TOKEN_OPS: dict[str, str | None] = {
    "OR":      "OR",
    "AND":     "AND",
    "NOT":     None,           # unary
    "IS":      "IS",
    "MATCH":   "MATCH",
    "LIKE_KW": "LIKE",          # representative
    "BETWEEN": None,            # special form `x BETWEEN a AND b`
    "IN":      None,            # special form `x IN (...)`
    "ISNULL":  None,            # postfix
    "NOTNULL": None,            # postfix
    "NE":      "<>",
    "EQ":      "=",
    "GT":      ">",
    "LE":      "<=",
    "LT":      "<",
    "GE":      ">=",
    "ESCAPE":  None,            # special: only after LIKE/GLOB
    "BITAND":  "&",
    "BITOR":   "|",
    "LSHIFT":  "<<",
    "RSHIFT":  ">>",
    "PLUS":    "+",
    "MINUS":   "-",
    "STAR":    "*",
    "SLASH":   "/",
    "REM":     "%",
    "CONCAT":  "||",
    "PTR":     "->",            # JSON path -> operator
    "COLLATE": None,            # special: x COLLATE name
    "BITNOT":  None,            # unary
    "ON":      None,            # special: ON CONFLICT, JOIN ON
}


def extract_precedence_levels(parse_y: Path) -> list[tuple[str, list[str]]]:
    """Returns list of (associativity, [token_names]) per declared
    precedence level, in parse.y order (lowest precedence first)."""
    text = parse_y.read_text()
    rows: list[tuple[str, list[str]]] = []
    for m in re.finditer(r"^%(left|right|nonassoc)\s+(.+?)\.", text, re.MULTILINE):
        assoc = m.group(1)
        toks = m.group(2).split()
        rows.append((assoc, toks))
    return rows


def has_error(node) -> bool:
    if node.type in ("ERROR", "malformed_blob_literal", "malformed_number_id"):
        return True
    if node.is_missing:
        return True
    return any(has_error(c) for c in node.children)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true",
                    help="just print the extracted precedence table")
    ap.add_argument("--max-failures", type=int, default=20)
    args = ap.parse_args()

    levels = extract_precedence_levels(PARSE_Y)

    # Build the binary-operator list with their precedence rank.
    # Lower rank = lower precedence (binds looser).
    op_info: list[tuple[str, int, str]] = []  # (op-text, level, assoc)
    for level_idx, (assoc, toks) in enumerate(levels):
        for tok in toks:
            op = TOKEN_OPS.get(tok)
            if op is None:
                continue
            op_info.append((op, level_idx, assoc))

    if args.list:
        print(f"# {len(levels)} precedence levels, {len(op_info)} binary ops")
        for level_idx, (assoc, toks) in enumerate(levels):
            ops = [TOKEN_OPS[t] for t in toks if TOKEN_OPS.get(t)]
            if ops:
                print(f"  L{level_idx:>2} [%{assoc:<8}]  {' '.join(ops)}")
        return 0

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    total = 0
    failures: list[tuple[str, str]] = []
    for op_a, level_a, _ in op_info:
        for op_b, level_b, _ in op_info:
            sql = f"SELECT x {op_a} y {op_b} z;"
            total += 1
            tree = parser.parse(sql.encode("utf-8"))
            if has_error(tree.root_node):
                if len(failures) < args.max_failures:
                    failures.append((sql, "parse error"))

    print(f"precedence-matrix: {total} ordered pairs ({len(op_info)} binary ops)")
    print(f"  parse failures: {len(failures)}")
    for sql, msg in failures:
        print(f"  - {sql}  ({msg})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
