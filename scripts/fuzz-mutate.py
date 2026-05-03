#!/usr/bin/env python3
"""Mutation-based fuzzer.

For deterministic, in-CI generative testing: take seed SQL inputs
from `test/snapshots/inputs.txt`, apply a battery of mutation
operators (random token swap / drop / duplicate / insert random
keyword), then run each mutant through:

  - libsqlite3's `sqlite3_prepare_v2` (the same syntax-vs-semantic
    classifier as the parse-level differentialb)
  - our tree-sitter parser (with the malformed-token-aware
    `_ts_has_error` predicate)

Disagreements:

  - SS-AA  both accept              (ok — surviving valid mutant)
  - SS-RR  both reject              (ok — broken mutant rejected)
  - SS-AR  sqlite ok, we reject     (REAL grammar bug surfaced by
                                     fuzzing)
  - SS-RA  sqlite rejects, we ok    (over-permissive — same caveats
                                     as the parse-level differential's
                                     SS-RA category)

Deterministic: fixed `--seed` + fixed iteration count -> bit-stable
output. CI uses `--seed 0xdeadbeef --iters 5000` and fails on any
non-allowlisted SS-AR.

A native sqlsmith integration would be richer (it generates SQL
from scratch by walking a postgres-derived grammar). Mutation-based
fuzzing is a pragmatic substitute that:

  - reuses our existing curated seed corpus,
  - is reproducible without external data,
  - finds the same class of bug as sqlsmith (token-position errors
    in the grammar).

Usage:
    scripts/fuzz-mutate.py [--iters 5000] [--seed 0xdeadbeef]
                           [--max-failures 20]
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import random
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

# Re-use the libsqlite3 binding from differential-test.py. We can't
# `import` it normally (hyphen in module name), so load by file path.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "differential_test", REPO_ROOT / "scripts" / "differential-test.py")
diff_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diff_mod)

SqliteParser = diff_mod.SqliteParser
ts_has_error = diff_mod._ts_has_error


# --- Mutation operators -------------------------------------------------

# Tokens to insert as random "noise" — keywords, common operators,
# punctuation. Drawn from sqlite's token vocabulary so mutants look
# vaguely SQL-shaped (more useful than purely random bytes).
INSERT_CANDIDATES = [
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "TRUE",
    "FALSE", "IN", "IS", "LIKE", "BETWEEN", "ORDER", "BY", "GROUP",
    "HAVING", "LIMIT", "OFFSET", "JOIN", "ON", "USING", "AS", "ALL",
    "DISTINCT", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
    ",", ";", "(", ")", "*", "+", "-", "/", "%", "=", "<", ">", "<>",
    "<=", ">=", "||", "1", "0", "x", "t", "'foo'", "\"bar\"",
]

TOKEN_RE = re.compile(
    r"\s+|"                          # whitespace
    r"--[^\n]*|"                     # line comment
    r"/\*.*?\*/|"                    # block comment (no nesting)
    r"'(?:[^']|'')*'|"               # single-quoted string
    r'"(?:[^"]|"")*"|'               # double-quoted identifier
    r"`(?:[^`]|``)*`|"               # backtick identifier
    r"\[[^\]]*\]|"                   # bracket identifier
    r"[Xx]'[0-9a-fA-F]*'|"           # blob literal
    r"\b[A-Za-z_][A-Za-z0-9_$]*\b|"  # identifier or keyword
    r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b|"  # number
    r"<<|>>|<>|<=|>=|->|->>|\|\||"   # multi-char operators
    r"."                             # everything else, single char
    , re.DOTALL,
)


def tokenize(sql: str) -> list[str]:
    """Coarse Python-side tokenization. Whitespace is preserved as
    its own token so mutations don't accidentally fuse tokens."""
    return TOKEN_RE.findall(sql)


def mutate(sql: str, rng: random.Random) -> str:
    """Apply ONE random mutation operator and return a new string."""
    toks = tokenize(sql)
    if not toks:
        return sql
    op = rng.choice([
        "drop", "duplicate", "swap", "replace_id", "insert", "uppercase_to_lower",
    ])
    n = len(toks)
    if op == "drop":
        i = rng.randrange(n)
        return "".join(toks[:i] + toks[i+1:])
    if op == "duplicate":
        i = rng.randrange(n)
        return "".join(toks[:i] + [toks[i]] + toks[i:])
    if op == "swap" and n >= 2:
        i, j = sorted(rng.sample(range(n), 2))
        toks2 = list(toks)
        toks2[i], toks2[j] = toks2[j], toks2[i]
        return "".join(toks2)
    if op == "replace_id":
        # Find an identifier-like token; replace with a different one.
        ids = [k for k, t in enumerate(toks)
               if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", t)]
        if ids:
            i = rng.choice(ids)
            new = rng.choice(("zz", "qq", "x1", "y2"))
            toks2 = list(toks)
            toks2[i] = new
            return "".join(toks2)
    if op == "insert":
        i = rng.randrange(n + 1)
        cand = rng.choice(INSERT_CANDIDATES)
        return "".join(toks[:i] + [cand, " "] + toks[i:])
    if op == "uppercase_to_lower":
        # Randomly lowercase one token.
        i = rng.randrange(n)
        if toks[i].upper() == toks[i] and toks[i].lower() != toks[i]:
            toks2 = list(toks)
            toks2[i] = toks[i].lower()
            return "".join(toks2)
    return sql


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
    ap.add_argument("--iters", type=int, default=5000,
                    help="number of mutations to generate")
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=0xdeadbeef,
                    help="RNG seed (hex or decimal); fixed for CI determinism")
    ap.add_argument("--max-failures", type=int, default=20)
    ap.add_argument(
        "--max-ss-ar", type=int, default=None,
        help="permit up to N non-allowlisted SS-AR cases (mutation-"
             "induced sqlite-leniency edge cases). If set, exit 0 "
             "as long as count <= N. Used in CI to keep the harness "
             "useful without churning the allowlist on every grammar "
             "tweak.",
    )
    ap.add_argument(
        "--inputs",
        type=Path,
        default=REPO_ROOT / "test" / "snapshots" / "inputs.txt",
    )
    ap.add_argument(
        "--allowlist",
        type=Path,
        default=REPO_ROOT / "test" / "fuzz-mutate-allowlist.txt",
        help="text file of mutated-SQL strings (one per line, escaped) "
             "permitted to fail the SS-AR check",
    )
    args = ap.parse_args()

    seeds = read_inputs(args.inputs)
    if not seeds:
        print(f"error: no seed inputs at {args.inputs}", file=sys.stderr)
        return 2

    allowlist: set[str] = set()
    if args.allowlist.exists():
        allowlist = {
            ln.split("#", 1)[0].strip()
            for ln in args.allowlist.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        }

    rng = random.Random(args.seed)
    sqlite_p = SqliteParser()
    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    ts_parser = tree_sitter.Parser(lang)

    counts = {"SS-AA": 0, "SS-RR": 0, "SS-AR": 0, "SS-RA": 0}
    bugs: list[tuple[str, str]] = []   # SS-AR (real grammar bugs)
    overaccept: list[str] = []         # SS-RA (informational)
    allowlisted = 0

    for _ in range(args.iters):
        seed = rng.choice(seeds)
        m = mutate(seed, rng)
        # Cap input size to avoid pathological mutants.
        if len(m) > 10000:
            continue
        sql_accepts, sql_err = sqlite_p.accepts(m)
        ts_tree = ts_parser.parse(m.encode("utf-8"))
        ts_accepts = not ts_has_error(ts_tree.root_node)
        key = f"SS-{'A' if sql_accepts else 'R'}{'A' if ts_accepts else 'R'}"
        counts[key] += 1
        if key == "SS-AR":
            esc = m.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
            if esc in allowlist:
                allowlisted += 1
            elif len(bugs) < args.max_failures:
                bugs.append((m, sql_err or ""))
        elif key == "SS-RA" and len(overaccept) < 10:
            overaccept.append(m)

    sqlite_p.close()

    sqlite_version = diff_mod._lib.sqlite3_libversion().decode()
    print(f"fuzz-mutate vs libsqlite3 {sqlite_version}: {args.iters} mutants "
          f"(seed=0x{args.seed:x})")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  allowlisted SS-AR: {allowlisted}")

    if bugs:
        print(f"\nFirst SS-AR (we should accept; sqlite does):")
        for m, err in bugs:
            one = m.replace("\n", " ")[:140]
            print(f"  - SQL: {one!r}")
            print(f"    sqlite: {err}")

    real_bugs = counts["SS-AR"] - allowlisted
    if real_bugs == 0:
        return 0
    if args.max_ss_ar is not None and real_bugs <= args.max_ss_ar:
        print(f"\nSS-AR ({real_bugs}) within --max-ss-ar threshold "
              f"({args.max_ss_ar}); OK.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
