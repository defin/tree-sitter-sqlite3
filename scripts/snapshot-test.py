#!/usr/bin/env python3
"""Tree-shape snapshot regression suite.

Each input in test/snapshots/inputs.txt has a corresponding snapshot
file at test/snapshots/<sha>.sexp containing the s-expression form of
that input's parse tree. This script compares current parses against
the stored snapshots, flagging any input whose tree shape changed.

The point: tree-sitter test catches divergence from hand-written
expected trees in the 147-fixture corpus. This catches silent shape
drift across hundreds more inputs we don't want to hand-write
expected trees for.

Modes:
  --check   (default) compare parses to stored snapshots; non-zero on
            any diff or any input missing its snapshot
  --update  rewrite all snapshots from current parser output (use when
            grammar changes are intentional and you've manually
            verified at least one resulting diff)

Inputs file format (test/snapshots/inputs.txt):
  - one SQL per line
  - newlines inside SQL escaped as \\n, tabs as \\t, backslash as \\\\
  - blank lines and `#`-prefixed lines ignored

Usage:
    scripts/snapshot-test.py [--check | --update] [--inputs FILE] [--dir DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent


def to_sexp(node, indent: int = 0) -> str:
    """Render a node as an indented s-expression. Stable, deterministic."""
    pad = "  " * indent
    if node.is_named:
        body = [f"{pad}({node.type}"]
        for child in node.children:
            if not child.is_named:
                continue
            # Find field name(s) for this child via the parent's
            # `field_name_for_child` — falls back to no field.
            idx = child.id
            # tree-sitter-py exposes per-child field name via the
            # parent's field_name_for_child(index) method (0-indexed
            # over all children, named or not).
            field_name = None
            for i in range(node.child_count):
                if node.child(i) is child or (
                    node.child(i).start_byte == child.start_byte
                    and node.child(i).end_byte == child.end_byte
                    and node.child(i).type == child.type
                ):
                    field_name = node.field_name_for_child(i)
                    break
            if field_name:
                body.append(f"\n{pad}  {field_name}:")
                # Render child without leading indent (it goes after the
                # field name on a continuation line).
                rendered = to_sexp(child, indent + 1).lstrip()
                body.append(f" {rendered}")
            else:
                body.append("\n")
                body.append(to_sexp(child, indent + 1))
        body.append(")")
        return "".join(body)
    # Anonymous tokens are not part of the snapshot.
    return ""


def snapshot_path(dir_: Path, sql: str) -> Path:
    h = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]
    return dir_ / f"{h}.sexp"


def render_snapshot(sql: str, parser) -> str:
    tree = parser.parse(sql.encode("utf-8"))
    sexp = to_sexp(tree.root_node).strip() + "\n"
    # Snapshot file format: input on top as comment lines, then ---,
    # then the sexp. Makes it easier to review diffs.
    header_lines = ["# input:"]
    for line in sql.splitlines() or [sql]:
        header_lines.append(f"#   {line}")
    return "\n".join(header_lines) + "\n---\n" + sexp


def parse_snapshot(text: str) -> str:
    """Return just the sexp body of a snapshot file."""
    parts = text.split("\n---\n", 1)
    return parts[1].strip() + "\n" if len(parts) == 2 else text.strip() + "\n"


def read_inputs(path: Path) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        if not raw or raw.startswith("#"):
            continue
        sql = raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        out.append(sql)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", default=True)
    g.add_argument("--update", action="store_true")
    ap.add_argument("--inputs", type=Path,
                    default=REPO_ROOT / "test" / "snapshots" / "inputs.txt")
    ap.add_argument("--dir", type=Path,
                    default=REPO_ROOT / "test" / "snapshots")
    ap.add_argument("--max-failures", type=int, default=10)
    args = ap.parse_args()

    inputs = read_inputs(args.inputs)
    if not inputs:
        print(f"error: no inputs found at {args.inputs}", file=sys.stderr)
        return 2

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    args.dir.mkdir(parents=True, exist_ok=True)

    if args.update:
        existing = {p.name for p in args.dir.glob("*.sexp")}
        wanted: set[str] = set()
        for sql in inputs:
            path = snapshot_path(args.dir, sql)
            wanted.add(path.name)
            content = render_snapshot(sql, parser)
            path.write_text(content)
        # Remove orphaned snapshots.
        removed = 0
        for stale in existing - wanted:
            (args.dir / stale).unlink()
            removed += 1
        print(f"updated {len(wanted)} snapshots; removed {removed} stale")
        return 0

    # --check mode
    diffs: list[tuple[str, str, str, Path]] = []
    missing: list[tuple[str, Path]] = []
    for sql in inputs:
        path = snapshot_path(args.dir, sql)
        actual = render_snapshot(sql, parser)
        if not path.exists():
            missing.append((sql, path))
            continue
        expected = path.read_text()
        if actual != expected:
            diffs.append((sql, parse_snapshot(expected), parse_snapshot(actual), path))

    print(f"snapshots: {len(inputs)} inputs")
    print(f"  diffs:   {len(diffs)}")
    print(f"  missing: {len(missing)}")

    for sql, exp, act, path in diffs[: args.max_failures]:
        one = sql.replace("\n", " ")[:120]
        print(f"\n--- {path.name}")
        print(f"  SQL:      {one}")
        print(f"  expected: {exp.splitlines()[0] if exp else '<empty>'}")
        print(f"  actual:   {act.splitlines()[0] if act else '<empty>'}")
    for sql, path in missing[: args.max_failures]:
        one = sql.replace("\n", " ")[:120]
        print(f"\nMISSING {path.name}")
        print(f"  SQL: {one}")

    if diffs or missing:
        print(
            "\nTo regenerate snapshots after intentional grammar changes, "
            "run:\n  scripts/snapshot-test.py --update"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
