#!/usr/bin/env python3
"""Extract SQL fragments from sqlite's TCL .test files.

The sqlite test suite is written in TCL. SQL fragments appear as the
braced argument to a small set of test-framework procs:

    execsql {SQL}
    catchsql {SQL}
    db eval {SQL}
    do_execsql_test NAME {SQL} {EXPECTED}
    do_catchsql_test NAME {SQL} {EXPECTED}

This extractor finds every such call, lifts the braced SQL, and writes
one fragment per output line (newlines inside the SQL are escaped to
\\n so the output is line-oriented and easy to feed into a runner).

Fragments that contain TCL substitutions ($var, [expr ...], etc.) are
SKIPPED — we cannot resolve the substitution without running TCL, and
treating $var as raw SQL would produce false-positive parse failures.

Output format (one fragment per line):

    <source-file>:<line>\t<sql-with-newlines-escaped>

Usage:
    extract-sql-fragments.py vendor/sqlite-test-corpus/test/*.test > fragments.txt
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator

# Procs whose first OR designated brace argument is SQL.
# Map proc-name -> 0-indexed position of the SQL argument among
# brace-quoted arguments encountered after the proc name.
#
# Note: the test-name argument to do_*_test is a bareword (not a brace
# argument), so for do_execsql_test the SQL is brace-arg #0, NOT #1.
SQL_PROCS = {
    "execsql": 0,
    "catchsql": 0,
    "explain": 0,        # `explain SQL` debug helper in tester.tcl
    "do_execsql_test": 0,
    "do_catchsql_test": 0,
    "do_eqp_test": 0,
}

# `db eval {SQL}` is also common; treat as a special two-token form.
DB_EVAL_RE = re.compile(r"\b(?:db|db2|db3)\s+eval\s*\{")

# A brace-quoted TCL argument starts with `{` at a word boundary. We
# scan from there with bracket counting, honoring backslash-escapes.
PROC_NAME_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in SQL_PROCS) + r")\b"
)

# Heuristic: skip fragments that look like they need TCL substitution.
# These tokens never appear in valid sqlite SQL but routinely appear in
# .test fragments where the test framework substitutes them at runtime.
# Patterns (left to right):
#   $name / $::name      TCL scalar / namespace var
#   ${name} / ${::name}  TCL braced var substitution
#   [<word> ...          TCL command substitution
#   %name%               .test placeholder (e.g. %WO%, %DEF%) used by some
#                        files for build-time substitution
TCL_SUB_RE = re.compile(
    r"\$[A-Za-z_:]|"
    r"\$\{|"
    r"\[[a-z]+\s|"
    r"%[A-Za-z_]+%"
)

# TCL line-comment: `#` at the start of a line (modulo whitespace) inside
# the braced argument. tester.tcl strips these before passing to sqlite.
TCL_LINE_COMMENT_RE = re.compile(r"(?m)^\s*#[^\n]*$")

# Common TCL command words that appear at the start of leaked-non-SQL
# fragments. If a fragment's first non-whitespace word is one of these
# AND none of the SQL_KEYWORDS appear, treat it as a TCL leak rather
# than a grammar bug. Conservative list — adding a word here silences
# real grammar bugs if SQL fragments happen to start with the same word.
TCL_LEAK_FIRST_WORD = frozenset({
    "lappend", "lindex", "llength", "lrange", "lreplace", "lset",
    "set", "unset", "incr", "string", "expr", "format", "puts",
    "list", "dict", "array", "regexp", "regsub", "scan",
    "if", "while", "for", "foreach", "switch", "catch", "return",
    "proc", "global", "namespace", "variable", "uplevel", "upvar",
    "subst", "eval", "after", "vwait", "trace", "info", "file",
    "open", "close", "read", "gets", "fconfigure",
    "execsql", "catchsql", "db",
})

# A SQL fragment should contain at least one of these top-level
# statement keywords. Used together with TCL_LEAK_FIRST_WORD.
SQL_KEYWORDS_RE = re.compile(
    r"(?i)\b(?:select|insert|update|delete|create|drop|alter|"
    r"attach|detach|begin|commit|rollback|savepoint|release|"
    r"pragma|reindex|analyze|explain|vacuum|with|values|"
    r"replace|truncate)\b"
)


def looks_like_tcl_leak(sql: str) -> bool:
    s = sql.lstrip()
    if not s:
        return False
    first = s.split(maxsplit=1)[0].lower().rstrip(":")
    # SQL-proc names at the start of a fragment ALWAYS indicate a leak:
    # we extracted the wrapping `do_test { execsql {...} }` body instead
    # of recursing into the inner execsql call. Skip regardless of
    # whether SQL keywords appear inside.
    if first in {"execsql", "catchsql", "db", "db2", "db3"}:
        return True
    if first not in TCL_LEAK_FIRST_WORD:
        return False
    return SQL_KEYWORDS_RE.search(sql) is None


def find_balanced_brace(text: str, start: int) -> int:
    """Given text[start] == '{', return index just past the matching '}'.

    Honors TCL's backslash-escape rule: '\\{' and '\\}' don't count.
    Returns -1 on imbalance.
    """
    assert text[start] == "{"
    depth = 0
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def extract_fragments(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (line_number, sql) for every SQL fragment in path."""
    text = path.read_text(encoding="utf-8", errors="replace")

    # Pre-compute line starts so we can map char-offset to line number.
    line_starts = [0]
    for i, c in enumerate(text):
        if c == "\n":
            line_starts.append(i + 1)

    def line_of(offset: int) -> int:
        # Binary search would be faster; linear is fine for our scale.
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1  # 1-indexed

    # Pass 1: SQL_PROCS calls. For each match, scan forward collecting
    # brace-quoted arguments until we hit the configured position.
    for m in PROC_NAME_RE.finditer(text):
        proc = m.group(1)
        sql_pos = SQL_PROCS[proc]
        # Walk forward from end of proc name, skipping non-brace tokens
        # (the test name, flags like -dialect=, etc.) and counting brace
        # arguments.
        i = m.end()
        n = len(text)
        seen_braces = 0
        # Limit scan to the next ~4KB so a missing brace doesn't run away.
        limit = min(n, i + 4096)
        while i < limit:
            c = text[i]
            if c == "{":
                end = find_balanced_brace(text, i)
                if end < 0:
                    break
                if seen_braces == sql_pos:
                    yield line_of(i), text[i + 1 : end - 1]
                    break
                seen_braces += 1
                i = end
                continue
            # Bail if we encounter a TCL double-quoted string, a TCL
            # variable substitution ($var), or a TCL command
            # substitution ([...]) before our brace argument. All three
            # involve runtime substitution we cannot resolve; continuing
            # past them would land on the NEXT brace, which is typically
            # the expected-result argument, not SQL.
            if c == '"' or c == '$' or c == "[":
                break
            # Bail at a closing `}` we see before our `{` argument. The
            # `}` closes the surrounding TCL block (e.g. the body of a
            # do_test), so anything after it is no longer an argument
            # to our SQL proc — typically the EXPECTED result of the
            # do_test, which is TCL-formatted, not SQL.
            if c == "}":
                break
            i += 1

    # Pass 2: `db eval {SQL}` form.
    for m in DB_EVAL_RE.finditer(text):
        i = m.end() - 1  # back up to the '{'
        end = find_balanced_brace(text, i)
        if end < 0:
            continue
        yield line_of(i), text[i + 1 : end - 1]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    paths = [Path(a) for a in argv]
    total = 0
    skipped_subst = 0
    skipped_empty = 0
    skipped_tcl = 0
    out = sys.stdout
    for p in paths:
        if not p.is_file():
            print(f"warning: not a file: {p}", file=sys.stderr)
            continue
        for line, sql in extract_fragments(p):
            # tester.tcl strips `#` line-comments before passing the
            # braced argument to sqlite; we do the same so they don't
            # confuse downstream parsing.
            sql = TCL_LINE_COMMENT_RE.sub("", sql)
            sql_stripped = sql.strip()
            if not sql_stripped:
                skipped_empty += 1
                continue
            if TCL_SUB_RE.search(sql_stripped):
                skipped_subst += 1
                continue
            if looks_like_tcl_leak(sql_stripped):
                skipped_tcl += 1
                continue
            # Escape newlines for line-oriented output.
            escaped = sql.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
            out.write(f"{p}:{line}\t{escaped}\n")
            total += 1

    print(
        f"# extracted {total} fragments; "
        f"skipped {skipped_subst} (TCL substitution), "
        f"{skipped_tcl} (TCL leak), "
        f"{skipped_empty} (empty)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
