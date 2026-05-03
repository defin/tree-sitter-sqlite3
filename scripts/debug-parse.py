#!/usr/bin/env python3
"""Quick parser debug helper. Reads SQL fragments from argv (one per
arg) or stdin (one per line) and reports ERROR/MISSING node detail
plus a truncated s-expression. Useful for triaging upstream-corpus
harness failures.

Usage:
    scripts/debug-parse.py "SELECT 1" "SELECT count(ORDER BY a) FROM t"
    echo 'SELECT 1' | scripts/debug-parse.py
"""

from __future__ import annotations
import sys
import tree_sitter, tree_sitter_sqlite3


def walk(node, out):
    if node.type == "ERROR" or node.is_missing:
        out.append((node.type, node.start_point, node.end_point, node.is_missing))
    for c in node.children:
        walk(c, out)


def main(argv: list[str]) -> int:
    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)
    inputs = argv or [line.rstrip("\n") for line in sys.stdin if line.strip()]
    for sql in inputs:
        print(f"--- {sql}")
        tree = parser.parse(sql.encode())
        errs: list = []
        walk(tree.root_node, errs)
        if errs:
            for e in errs:
                print(f"  FAIL {e}")
        else:
            print("  ok")
        s = str(tree.root_node)
        print(f"  {s[:240]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
