#!/usr/bin/env python3
"""Extras-placement matrix.

Comments and whitespace are 'extras' in tree-sitter and may legally
appear between any two tokens. This harness generates a matrix of
variants by inserting `-- comment\\n` and `/* comment */` between every
pair of adjacent tokens in a set of seed inputs, then asserts:

  1. Every variant parses successfully (no ERROR / MISSING nodes).
  2. Every variant produces the SAME parse tree as the no-comment
     original — the comment is in extras, so the named tree shape
     should be invariant.

A failure indicates either:
  - the grammar has a token rule that swallows surrounding whitespace
    in a way that breaks when a comment is inserted, or
  - extras placement is incorrectly broken in the resulting tree
    structure (e.g. a comment is being attached to the wrong parent).

Both are real bugs that hand-written fixtures don't catch.

Seed input set: test/snapshots/inputs.txt — already curated to cover
the major grammar paths.

Usage:
    scripts/extras-placement-test.py [--max-failures N] [--threshold F]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMENTS = ("-- spliced\n", "/* spliced */")


def has_error(node) -> bool:
    if node.type == "ERROR" or node.is_missing:
        return True
    return any(has_error(c) for c in node.children)


def tree_shape(node) -> tuple:
    """Recursive named-only shape, with line/block comments filtered.

    Returns (type, (children-shapes,...)) so two trees compare equal
    iff they have the same hierarchy of named non-comment nodes in
    the same order.
    """
    if node.type in ("line_comment", "block_comment"):
        return None
    children = []
    for c in node.children:
        if not c.is_named:
            continue
        s = tree_shape(c)
        if s is not None:
            children.append(s)
    return (node.type, tuple(children))


def leaf_token_offsets(node, out: list[int]) -> None:
    """Collect end-byte offsets of every named leaf in tree order.

    These offsets are the inter-token gaps where we splice comments.
    We use END byte of one leaf as the splice point for the gap before
    the NEXT leaf. The very first leaf's start has no 'before' gap
    (handled separately by inserting at byte 0).
    """
    if node.is_named and not node.children:
        out.append(node.end_byte)
        return
    for c in node.children:
        leaf_token_offsets(c, out)


def gen_variants(sql: str, ends: list[int]) -> list[tuple[int, str, str]]:
    """For every gap, yield (gap_index, comment, variant_sql)."""
    variants: list[tuple[int, str, str]] = []
    sql_b = sql.encode("utf-8")
    # Splice positions: byte 0 (before everything) and after each leaf.
    splice_points = [0] + ends
    for i, off in enumerate(splice_points):
        for c in COMMENTS:
            cb = c.encode("utf-8")
            variant = sql_b[:off] + cb + sql_b[off:]
            try:
                variants.append((i, c, variant.decode("utf-8")))
            except UnicodeDecodeError:
                continue
    return variants


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-failures", type=int, default=15)
    ap.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="pass rate floor (0.0-1.0); below => exit non-zero",
    )
    ap.add_argument(
        "--inputs",
        type=Path,
        default=REPO_ROOT / "test" / "snapshots" / "inputs.txt",
    )
    args = ap.parse_args()

    if not args.inputs.exists():
        print(f"error: inputs file missing: {args.inputs}", file=sys.stderr)
        return 2

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    seeds: list[str] = []
    for line in args.inputs.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        s = line.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        seeds.append(s)

    total = 0
    parse_failures: list[tuple[str, int, str, str]] = []  # (seed, gap, comment, variant)
    shape_failures: list[tuple[str, int, str, str]] = []
    skipped_seeds = 0

    for seed in seeds:
        baseline = parser.parse(seed.encode("utf-8"))
        if has_error(baseline.root_node):
            # Don't run extras tests on seeds that already fail to
            # parse cleanly — the harness assumes a clean baseline.
            skipped_seeds += 1
            continue
        baseline_shape = tree_shape(baseline.root_node)
        ends: list[int] = []
        leaf_token_offsets(baseline.root_node, ends)
        for gap_i, comment, variant_sql in gen_variants(seed, ends):
            total += 1
            tree = parser.parse(variant_sql.encode("utf-8"))
            if has_error(tree.root_node):
                if len(parse_failures) < args.max_failures:
                    parse_failures.append((seed, gap_i, comment, variant_sql))
                continue
            if tree_shape(tree.root_node) != baseline_shape:
                if len(shape_failures) < args.max_failures:
                    shape_failures.append((seed, gap_i, comment, variant_sql))

    fails = len(parse_failures) + len(shape_failures)
    print(f"extras-placement: {len(seeds) - skipped_seeds} seeds, {total} variants")
    print(f"  parse failures: {sum(1 for _ in parse_failures)} (cap {args.max_failures})")
    print(f"  shape failures: {sum(1 for _ in shape_failures)} (cap {args.max_failures})")
    print(f"  skipped seeds (baseline ERROR):  {skipped_seeds}")

    for seed, gap, comment, variant in parse_failures[:5]:
        seed_one = seed.replace("\n", " ")[:100]
        var_one = variant.replace("\n", " ")[:140]
        print(f"\n  [parse-fail] gap {gap} comment {comment!r}")
        print(f"    seed:    {seed_one}")
        print(f"    variant: {var_one}")
    for seed, gap, comment, variant in shape_failures[:5]:
        seed_one = seed.replace("\n", " ")[:100]
        var_one = variant.replace("\n", " ")[:140]
        print(f"\n  [shape-fail] gap {gap} comment {comment!r}")
        print(f"    seed:    {seed_one}")
        print(f"    variant: {var_one}")

    if total == 0:
        return 1
    pass_rate = (total - fails) / total
    print(f"\n  pass rate: {pass_rate:.4f}")

    if fails == 0:
        return 0
    if args.threshold is not None and pass_rate >= args.threshold:
        print(f"  pass rate >= threshold {args.threshold:.4f}; OK")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
