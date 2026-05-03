#!/usr/bin/env python3
"""Walks the full tree (including anonymous children) for diagnostics."""
import sys, tree_sitter, tree_sitter_sqlite3
lang = tree_sitter.Language(tree_sitter_sqlite3.language())
parser = tree_sitter.Parser(lang)
for sql in sys.argv[1:]:
    tree = parser.parse(sql.encode())
    def walk(n, depth=0):
        kind = "named" if n.is_named else "anon"
        text_repr = bytes(n.text)[:40] if n.text else b''
        print(" " * depth + f"[{kind}] {n.type!r:30} {n.start_byte}..{n.end_byte} text={text_repr!r}")
        for c in n.children:
            walk(c, depth + 1)
    print(f"--- {sql!r}")
    walk(tree.root_node)
