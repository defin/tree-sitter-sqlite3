#!/usr/bin/env python3
"""Roundtrip property tests.

Asserts three invariants on every successfully-parsed input:

  1. Root range covers the whole input:
        root.start_byte == 0
        root.end_byte   == len(input)

  2. Byte-for-byte concatenation of leaf text reproduces the input:
        ''.join(leaf.text for leaf in walk_leaves(root)) == input

  3. Sibling ranges are non-overlapping and weakly monotonic
     (a child cannot start before its predecessor sibling ends).

Reads inputs from stdin (one SQL per line, `\\n`-escaped) OR from
test/snapshots/inputs.txt (default). Designed to share input format
with the snapshot suite.

A failure here usually means an extras-handling bug (a comment got
attached to the wrong parent, whitespace was eaten by a token rule
that shouldn't, etc.) — silent tree-shape corruption that doesn't
surface as an ERROR node.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterator

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent


def walk_leaves(node) -> Iterator:
    """Yield every leaf node in document order, including extras."""
    if node.child_count == 0:
        yield node
        return
    for c in node.children:
        yield from walk_leaves(c)


def check_root_range(root, source: bytes) -> str | None:
    if root.start_byte != 0:
        return f"root.start_byte = {root.start_byte}, expected 0"
    if root.end_byte != len(source):
        return f"root.end_byte = {root.end_byte}, expected {len(source)}"
    return None


def check_byte_roundtrip(root, source: bytes) -> str | None:
    """Concatenated leaf bytes (with inter-leaf gaps preserved by
    using byte-offsets rather than .text) should equal the source."""
    pos = 0
    pieces: list[bytes] = []
    for leaf in walk_leaves(root):
        if leaf.start_byte > pos:
            # Gap between leaves — must be all whitespace OR contained
            # in extras nodes that ARE leaves themselves.  In tree-
            # sitter, comments are leaf-named; whitespace is not in
            # the tree at all, so a gap of pure whitespace is normal.
            gap = source[pos:leaf.start_byte]
            if gap.strip():
                return (
                    f"non-whitespace gap at {pos}..{leaf.start_byte}: "
                    f"{gap!r}"
                )
            pieces.append(gap)
        pieces.append(source[leaf.start_byte:leaf.end_byte])
        pos = leaf.end_byte
    if pos < len(source):
        tail = source[pos:]
        if tail.strip():
            return f"non-whitespace tail at {pos}..{len(source)}: {tail!r}"
        pieces.append(tail)
    reconstructed = b"".join(pieces)
    if reconstructed != source:
        # Find the first byte of divergence.
        m = min(len(reconstructed), len(source))
        for i in range(m):
            if reconstructed[i] != source[i]:
                return (
                    f"byte mismatch at offset {i}: "
                    f"src={source[max(0, i-5):i+10]!r} "
                    f"reconstructed={reconstructed[max(0, i-5):i+10]!r}"
                )
        return (
            f"length mismatch: src={len(source)} "
            f"reconstructed={len(reconstructed)}"
        )
    return None


def check_sibling_monotonic(node) -> str | None:
    prev_end = node.start_byte
    for c in node.children:
        if c.start_byte < prev_end:
            return (
                f"child {c.type!r} starts at {c.start_byte}, "
                f"before prev sibling end {prev_end} (parent {node.type!r})"
            )
        prev_end = c.end_byte
        nested = check_sibling_monotonic(c)
        if nested is not None:
            return nested
    return None


def has_error_or_missing(node) -> bool:
    if node.type == "ERROR" or node.is_missing:
        return True
    return any(has_error_or_missing(c) for c in node.children)


def read_inputs(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for raw in path.read_text().splitlines():
        if not raw or raw.startswith("#"):
            continue
        out.append(
            raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--inputs",
        type=Path,
        default=REPO_ROOT / "test" / "snapshots" / "inputs.txt",
    )
    ap.add_argument("--max-failures", type=int, default=10)
    args = ap.parse_args()

    inputs = read_inputs(args.inputs)
    if not inputs and not sys.stdin.isatty():
        for raw in sys.stdin:
            raw = raw.rstrip("\n")
            if not raw:
                continue
            inputs.append(
                raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
            )
    if not inputs:
        print(f"error: no inputs found", file=sys.stderr)
        return 2

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    counts = {"checked": 0, "skipped_error": 0, "fail_root": 0,
              "fail_roundtrip": 0, "fail_monotonic": 0}
    failures: list[tuple[str, str, str]] = []  # (which-check, sql, msg)

    for sql in inputs:
        source = sql.encode("utf-8")
        tree = parser.parse(source)
        if has_error_or_missing(tree.root_node):
            counts["skipped_error"] += 1
            continue
        counts["checked"] += 1

        for which, fn in (
            ("root", lambda r=tree.root_node: check_root_range(r, source)),
            ("roundtrip", lambda r=tree.root_node: check_byte_roundtrip(r, source)),
            ("monotonic", lambda r=tree.root_node: check_sibling_monotonic(r)),
        ):
            err = fn()
            if err is not None:
                counts[f"fail_{which}"] += 1
                if len(failures) < args.max_failures:
                    failures.append((which, sql, err))

    fails = counts["fail_root"] + counts["fail_roundtrip"] + counts["fail_monotonic"]
    print(f"roundtrip property: {counts['checked']} inputs checked")
    print(f"  skipped (parse ERROR/MISSING): {counts['skipped_error']}")
    print(f"  fail_root (range mismatch):    {counts['fail_root']}")
    print(f"  fail_roundtrip (byte diff):    {counts['fail_roundtrip']}")
    print(f"  fail_monotonic (sibling gap):  {counts['fail_monotonic']}")

    if failures:
        print("\nFirst failures:")
        for which, sql, msg in failures:
            one = sql.replace("\n", " ")[:120]
            print(f"  [{which}] {msg}")
            print(f"    SQL: {one}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
