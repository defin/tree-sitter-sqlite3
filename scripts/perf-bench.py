#!/usr/bin/env python3
"""Performance regression benchmarks.

Measures parse time on a curated set of inputs covering common shapes
plus pathological cases (deep nesting, long IN-lists, wide statements).
Persists results to test/perf-baseline.json. CI failure if any
benchmark regresses by more than the configured tolerance.

Modes:
  --bench   (default) measure each benchmark, compare to baseline,
            fail if any regresses past tolerance.
  --update  rewrite the baseline from current measurements.

Each benchmark runs N iterations to amortise jitter; we record the
median time. The baseline stores median µs/parse per benchmark.

Usage:
    scripts/perf-bench.py [--bench | --update] [--tolerance 0.30]

Tolerance defaults to 30% — generous enough to absorb CI runner
jitter but tight enough to catch a pathological grammar regression.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import median

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "test" / "perf-baseline.json"


# Curated benchmarks. Each entry: (name, iterations, sql).
# Names should be stable — they're keys in the baseline JSON.
BENCHMARKS: list[tuple[str, int, str]] = [
    # Small one-liners — typical IDE-incremental-parse cost.
    ("select-1",                   1000, "SELECT 1;"),
    ("select-star",                1000, "SELECT * FROM users WHERE id = 5;"),
    ("insert-values",              1000, "INSERT INTO t1(a, b, c) VALUES (1, 'x', NULL);"),
    ("update-where",               1000, "UPDATE t1 SET a = a + 1 WHERE b > 10;"),
    ("delete-where",               1000, "DELETE FROM t1 WHERE id = 42;"),

    # Medium DDL.
    ("create-table",                500,
     "CREATE TABLE t1(a INTEGER PRIMARY KEY, b TEXT NOT NULL, c REAL DEFAULT 0.0, "
     "d BLOB, e DATETIME, FOREIGN KEY(b) REFERENCES other(name));"),
    ("create-trigger",              500,
     "CREATE TRIGGER tr1 AFTER INSERT ON t1 FOR EACH ROW BEGIN "
     "UPDATE counts SET n = n + 1 WHERE table_name = 't1'; END;"),

    # Compound and CTE.
    ("compound-union",              500,
     "SELECT a FROM t1 WHERE b > 0 UNION ALL SELECT a FROM t2 WHERE c < 100 "
     "EXCEPT SELECT a FROM t3 ORDER BY a LIMIT 50;"),
    ("cte-recursive",               500,
     "WITH RECURSIVE c(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM c WHERE x<100) "
     "SELECT x, x*x FROM c;"),

    # Window functions.
    ("window-rank-over-partition",  500,
     "SELECT name, dept, salary, "
     "RANK() OVER (PARTITION BY dept ORDER BY salary DESC) AS r "
     "FROM employees WHERE salary > 50000;"),

    # Pathological: deeply nested expression.
    ("deep-paren-expr",              50,
     "SELECT " + "(" * 200 + "1" + ")" * 200 + ";"),
    # Pathological: long IN list.
    ("long-in-list",                 50,
     "SELECT * FROM t WHERE id IN (" +
     ", ".join(str(i) for i in range(500)) + ");"),
    # Pathological: many comma-separated columns.
    ("wide-select-columns",         100,
     "SELECT " + ", ".join(f"col_{i}" for i in range(200)) + " FROM t1;"),
    # Pathological: deeply nested CASE.
    ("deep-case",                    50,
     "SELECT " +
     "".join("CASE WHEN x > {} THEN ".format(i) for i in range(50)) +
     "0" + " ELSE 0 END" * 50 + ";"),

    # Multi-statement.
    ("multi-statement-50",           50,
     ";\n".join(f"INSERT INTO t1 VALUES({i})" for i in range(50)) + ";"),
]


def measure(parser: "tree_sitter.Parser", sql: str, iterations: int) -> float:
    """Return median microseconds per parse over `iterations` runs."""
    source = sql.encode("utf-8")
    samples_us: list[float] = []
    # Warmup
    for _ in range(min(5, iterations)):
        parser.parse(source)
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        parser.parse(source)
        t1 = time.perf_counter_ns()
        samples_us.append((t1 - t0) / 1000.0)
    return median(samples_us)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--bench", action="store_true", default=True)
    g.add_argument("--update", action="store_true",
                   help="rewrite baseline with current measurements")
    ap.add_argument("--tolerance", type=float, default=0.30,
                    help="max relative regression allowed per benchmark")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()

    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    parser = tree_sitter.Parser(lang)

    print(f"perf-bench: {len(BENCHMARKS)} benchmarks")
    results: dict[str, float] = {}
    for name, iters, sql in BENCHMARKS:
        us = measure(parser, sql, iters)
        results[name] = us

    if args.update:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(
            json.dumps({"unit": "us-per-parse-median",
                        "tolerance": args.tolerance,
                        "benchmarks": results},
                       indent=2, sort_keys=True) + "\n"
        )
        print(f"wrote baseline to {BASELINE_PATH}")
        for name, us in sorted(results.items()):
            print(f"  {name:32}  {us:>8.1f} us")
        return 0

    # --bench mode: compare to baseline.
    if not BASELINE_PATH.exists():
        print(f"error: baseline missing at {BASELINE_PATH}; run --update", file=sys.stderr)
        return 2
    baseline_doc = json.loads(BASELINE_PATH.read_text())
    baseline = baseline_doc.get("benchmarks", {})

    regressions: list[tuple[str, float, float, float]] = []
    improvements: list[tuple[str, float, float, float]] = []
    for name, us in sorted(results.items()):
        base = baseline.get(name)
        if base is None:
            print(f"  [NEW]  {name:32}  {us:>8.1f} us  (no baseline; --update to record)")
            continue
        ratio = us / base
        delta_pct = (ratio - 1.0) * 100.0
        marker = "     " if abs(delta_pct) < 5 else ("SLOW " if delta_pct > 0 else "fast ")
        if not args.summary_only:
            print(f"  {marker}  {name:32}  {us:>8.1f} us  (baseline {base:>7.1f}, "
                  f"{delta_pct:+5.1f}%)")
        if ratio > 1.0 + args.tolerance:
            regressions.append((name, base, us, delta_pct))
        elif ratio < 1.0 - args.tolerance:
            improvements.append((name, base, us, delta_pct))

    if improvements:
        print(f"\n{len(improvements)} significant improvements — "
              "consider --update to refresh baseline.")

    if regressions:
        print(f"\nFAIL: {len(regressions)} benchmark(s) regressed beyond "
              f"{args.tolerance:.0%} tolerance:")
        for name, base, us, delta in regressions:
            print(f"  {name}: {base:.1f} -> {us:.1f} us ({delta:+.1f}%)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
