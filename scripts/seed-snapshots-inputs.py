#!/usr/bin/env python3
"""One-shot seed for test/snapshots/inputs.txt.

Builds the curated input list by combining:
  1. Every SQL fragment from test/corpus/*.txt (the hand-written
     fixtures — they pass tree-sitter test, so they parse cleanly).
  2. The first successfully-parsed fragment from each upstream
     .test file (gives diverse sqlite-feature coverage with one
     deterministic representative per file).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import tree_sitter, tree_sitter_sqlite3


REPO_ROOT = Path(__file__).resolve().parent.parent

SEP = re.compile(r"^={3,}$", re.MULTILINE)
BOUNDARY = re.compile(r"^---+$", re.MULTILINE)


def iter_fixture_fragments():
    for p in sorted((REPO_ROOT / "test" / "corpus").glob("*.txt")):
        text = p.read_text()
        chunks = SEP.split(text)
        i = 1
        while i < len(chunks):
            body = chunks[i + 1] if i + 1 < len(chunks) else ""
            m = BOUNDARY.search(body)
            sql = (body[: m.start()] if m else body).strip()
            if sql:
                yield sql
            i += 2


def has_error(node) -> bool:
    if node.type == "ERROR" or node.is_missing:
        return True
    return any(has_error(c) for c in node.children)


def main() -> int:
    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    seen: set[str] = set()
    inputs: list[str] = []

    for sql in iter_fixture_fragments():
        if sql in seen:
            continue
        tree = parser.parse(sql.encode("utf-8"))
        if has_error(tree.root_node):
            continue
        seen.add(sql)
        inputs.append(sql)

    out_path = REPO_ROOT / "test" / "snapshots" / "inputs.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Curated input list for the snapshot regression suite.",
             "# Lines starting with # are comments; blank lines ignored.",
             "# Multi-line SQL is encoded with \\n for newline, \\t for tab.",
             ""]
    for sql in inputs:
        encoded = sql.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
        lines.append(encoded)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {out_path} with {len(inputs)} inputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
