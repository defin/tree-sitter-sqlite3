#!/usr/bin/env python3
"""Differential testing: tree-sitter-sqlite3 grammar vs libsqlite3.

For each SQL fragment we read from stdin (output of
extract-sql-fragments.py), we ask two questions:

  1. Does sqlite ACCEPT it? — i.e. does sqlite3_prepare_v2() succeed
     for every statement separated by `;` in the input?
  2. Does our grammar ACCEPT it? — i.e. does tree-sitter parse without
     producing any ERROR or MISSING node?

We classify each fragment into one of four buckets:

  SS-AA  both accept             (ok)
  SS-RR  both reject             (ok — they agree on rejection)
  SS-AR  sqlite accepts, we reject   (REAL BUG — grammar gap)
  SS-RA  sqlite rejects, we accept   (we are permissive — usually fine
                                       for a syntactic-only grammar,
                                       but may indicate over-acceptance)

Exit codes:
  0  -- no SS-AR cases (or all SS-AR cases are allowlisted)
  1  -- one or more SS-AR cases not on the allowlist
  2  -- usage / setup error

The allowlist works the same as parse-upstream-corpus.py.

Usage:
    scripts/extract-sql-fragments.py <test-files> \\
        | scripts/differential-test.py [--allowlist PATH] [--max-failures N]
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import sys
from pathlib import Path
from typing import Iterable, Iterator

try:
    import tree_sitter
    import tree_sitter_sqlite3
except ImportError as e:
    print(f"error: missing python deps ({e})", file=sys.stderr)
    sys.exit(2)


# --------------------------------------------------------------------------
# libsqlite3 binding via ctypes
# --------------------------------------------------------------------------

SQLITE_OK = 0


def _next_semicolon(buf: bytes, start: int) -> int:
    """Index just past the next `;` that lies OUTSIDE a string literal,
    quoted identifier, or comment. Returns len(buf) if none found."""
    n = len(buf)
    i = start
    while i < n:
        c = buf[i]
        if c == ord(";"):
            return i + 1
        if c == ord("'"):
            i += 1
            while i < n:
                if buf[i] == ord("'"):
                    if i + 1 < n and buf[i + 1] == ord("'"):
                        i += 2  # escaped quote
                        continue
                    i += 1  # closing quote
                    break
                i += 1
            continue
        if c == ord('"'):
            i += 1
            while i < n:
                if buf[i] == ord('"'):
                    if i + 1 < n and buf[i + 1] == ord('"'):
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if c == ord("[") :
            i += 1
            while i < n and buf[i] != ord("]"):
                i += 1
            i += 1
            continue
        if c == ord("`"):
            i += 1
            while i < n and buf[i] != ord("`"):
                i += 1
            i += 1
            continue
        if c == ord("-") and i + 1 < n and buf[i + 1] == ord("-"):
            # line comment to end-of-line
            i += 2
            while i < n and buf[i] != ord("\n"):
                i += 1
            continue
        if c == ord("/") and i + 1 < n and buf[i + 1] == ord("*"):
            # block comment to */
            i += 2
            while i + 1 < n and not (buf[i] == ord("*") and buf[i + 1] == ord("/")):
                i += 1
            i += 2
            continue
        i += 1
    return n


def _load_sqlite3() -> ctypes.CDLL:
    # Prefer the version-pinned libsqlite3 we build from amalgamation
    # in Dockerfile.dev (matches vendor/README.md). Fall back to system
    # if that's unavailable (e.g. ad-hoc local runs).
    for cand in (
        "/usr/local/lib/libsqlite3.so",
        "/usr/local/lib/libsqlite3.so.0",
    ):
        try:
            return ctypes.CDLL(cand)
        except OSError:
            continue
    name = ctypes.util.find_library("sqlite3")
    if name is None:
        for cand in (
            "/usr/lib/x86_64-linux-gnu/libsqlite3.so.0",
            "/usr/lib/x86_64-linux-gnu/libsqlite3.so",
        ):
            try:
                return ctypes.CDLL(cand)
            except OSError:
                continue
        raise RuntimeError("libsqlite3 not found on the system")
    return ctypes.CDLL(name)


_lib = _load_sqlite3()

_lib.sqlite3_libversion.argtypes = []
_lib.sqlite3_libversion.restype = ctypes.c_char_p
_lib.sqlite3_open.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
_lib.sqlite3_open.restype = ctypes.c_int
_lib.sqlite3_close.argtypes = [ctypes.c_void_p]
_lib.sqlite3_close.restype = ctypes.c_int
_lib.sqlite3_prepare_v2.argtypes = [
    ctypes.c_void_p,                 # db
    ctypes.c_char_p,                 # zSql
    ctypes.c_int,                    # nByte
    ctypes.POINTER(ctypes.c_void_p), # ppStmt
    ctypes.POINTER(ctypes.c_char_p), # pzTail
]
_lib.sqlite3_prepare_v2.restype = ctypes.c_int
_lib.sqlite3_finalize.argtypes = [ctypes.c_void_p]
_lib.sqlite3_finalize.restype = ctypes.c_int
_lib.sqlite3_errmsg.argtypes = [ctypes.c_void_p]
_lib.sqlite3_errmsg.restype = ctypes.c_char_p


class SqliteParser:
    """Wraps an in-memory libsqlite3 connection for parse-only checks."""

    def __init__(self) -> None:
        self._db = ctypes.c_void_p()
        rc = _lib.sqlite3_open(b":memory:", ctypes.byref(self._db))
        if rc != SQLITE_OK:
            raise RuntimeError("sqlite3_open(:memory:) failed")

    def close(self) -> None:
        if self._db:
            _lib.sqlite3_close(self._db)
            self._db = ctypes.c_void_p()

    # sqlite3_prepare_v2 also fails on semantic errors (no such table,
    # no such column, no such function, etc.) — those happen after
    # successful parse, during code-generation. We only want to count
    # SYNTAX failures here. Heuristic on the error message: anything
    # starting with one of these prefixes is a syntactic rejection.
    _SYNTAX_ERROR_PREFIXES = (
        "near ",
        "incomplete input",
        "unrecognized token",
        "syntax error",
        "malformed ",
        '"', # e.g. '"FOO": syntax error'
    )

    @classmethod
    def _is_syntax_error(cls, msg: str) -> bool:
        m = msg.lower()
        if any(m.startswith(p) for p in cls._SYNTAX_ERROR_PREFIXES):
            return True
        # Some sqlite messages embed "syntax error" mid-string.
        return "syntax error" in m or "unrecognized token" in m

    def accepts(self, sql: str) -> tuple[bool, str | None]:
        """Return (accepts-syntactically, error-message-if-any).

        On rejection, the error message is the syntax-error message
        from sqlite. On acceptance, returns None as the message
        (semantic errors are squashed since we treat them as accept).
        """
        sql_b = sql.encode("utf-8")
        offset = 0
        n = len(sql_b)
        while offset < n:
            z = ctypes.c_char_p(sql_b[offset:])
            stmt = ctypes.c_void_p()
            pz_tail = ctypes.c_char_p()
            rc = _lib.sqlite3_prepare_v2(
                self._db, z, -1, ctypes.byref(stmt), ctypes.byref(pz_tail)
            )
            if rc != SQLITE_OK:
                err = _lib.sqlite3_errmsg(self._db)
                msg = err.decode("utf-8", errors="replace") if err else ""
                _lib.sqlite3_finalize(stmt)
                if self._is_syntax_error(msg):
                    return False, msg
                # Semantic error: skip past the next `;` (or to EOF)
                # so we can continue checking subsequent statements.
                # CRITICAL: don't land on a `;` inside a string literal,
                # quoted identifier, or comment — those would split a
                # well-formed statement mid-way and produce a spurious
                # syntax error on the resumed prepare.
                offset = _next_semicolon(sql_b, offset)
                continue
            _lib.sqlite3_finalize(stmt)
            tail_bytes = pz_tail.value
            if tail_bytes is None or tail_bytes == b"":
                return True, None
            # ctypes.c_char_p decodes from the input pointer; the
            # difference between input start and tail is what we
            # consumed for THIS statement.
            consumed = len(sql_b) - offset - len(tail_bytes)
            if consumed <= 0:
                return True, None
            offset += consumed
        return True, None


# --------------------------------------------------------------------------
# tree-sitter side
# --------------------------------------------------------------------------


_MALFORMED_TYPES = {"malformed_blob_literal", "malformed_number_id"}


def _ts_has_error(node: "tree_sitter.Node") -> bool:
    if node.type == "ERROR" or node.is_missing:
        return True
    if node.type in _MALFORMED_TYPES:
        return True
    return any(_ts_has_error(c) for c in node.children)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def _read_fragments() -> Iterator[tuple[str, str]]:
    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        if not raw or raw.startswith("#"):
            continue
        loc, _, escaped = raw.partition("\t")
        if not escaped:
            continue
        sql = (
            escaped.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        )
        yield loc, sql


def _load_allowlist(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    out = set()
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-failures", type=int, default=20)
    ap.add_argument(
        "--allowlist",
        type=Path,
        default=Path("test/differential-allowlist.txt"),
    )
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument(
        "--dump-ss-ra",
        type=Path,
        help="dump every SS-RA case (loc, sql) to PATH for offline analysis",
    )
    ap.add_argument(
        "--dump-ss-ar",
        type=Path,
        help="dump every SS-AR case (loc, sql, sqlite-error) to PATH",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Pass rate floor for SS-AR cases (0.0-1.0); None => zero-tolerance",
    )
    args = ap.parse_args()

    allowlist = _load_allowlist(args.allowlist)

    sqlite_p = SqliteParser()
    lang = tree_sitter.Language(tree_sitter_sqlite3.language())
    ts_parser = tree_sitter.Parser(lang)

    counts = {"SS-AA": 0, "SS-RR": 0, "SS-AR": 0, "SS-RA": 0}
    real_bugs: list[tuple[str, str, str]] = []   # SS-AR
    over_accepts: list[tuple[str, str]] = []     # SS-RA (informational)
    all_ss_ar: list[tuple[str, str, str]] = []
    all_ss_ra: list[tuple[str, str, str]] = []
    allowlisted = 0
    total = 0

    for loc, sql in _read_fragments():
        total += 1
        sql_accepts, sql_err = sqlite_p.accepts(sql)
        ts_tree = ts_parser.parse(sql.encode("utf-8"))
        ts_accepts = not _ts_has_error(ts_tree.root_node)

        key = f"SS-{'A' if sql_accepts else 'R'}{'A' if ts_accepts else 'R'}"
        counts[key] += 1

        if key == "SS-AR":
            all_ss_ar.append((loc, sql, sql_err or "(no error message)"))
            if loc in allowlist:
                allowlisted += 1
            elif len(real_bugs) < args.max_failures:
                real_bugs.append((loc, sql, sql_err or "(no error message)"))
        elif key == "SS-RA":
            all_ss_ra.append((loc, sql, sql_err or "(no error message)"))
            if len(over_accepts) < args.max_failures:
                over_accepts.append((loc, sql))

    sqlite_p.close()

    sqlite_version = _lib.sqlite3_libversion().decode()
    print(f"differential vs libsqlite3 {sqlite_version}: {total} fragments")
    print(f"  SS-AA  both accept:        {counts['SS-AA']}")
    print(f"  SS-RR  both reject:        {counts['SS-RR']}")
    print(f"  SS-AR  sqlite OK, we ERR:  {counts['SS-AR']} (REAL BUGS)")
    print(f"  SS-RA  sqlite ERR, we OK:  {counts['SS-RA']} (over-acceptance)")
    print(f"  allowlisted SS-AR:         {allowlisted}")

    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")

    if args.dump_ss_ra:
        with args.dump_ss_ra.open("w") as f:
            for loc, sql, err in all_ss_ra:
                f.write(f"{loc}\t{_esc(err)}\t{_esc(sql)}\n")
    if args.dump_ss_ar:
        with args.dump_ss_ar.open("w") as f:
            for loc, sql, err in all_ss_ar:
                f.write(f"{loc}\t{_esc(err)}\t{_esc(sql)}\n")

    bugs = counts["SS-AR"] - allowlisted
    if real_bugs and not args.summary_only:
        print("\nFirst SS-AR (we should accept; sqlite does):")
        for loc, sql, err in real_bugs:
            print(f"  {loc}")
            print(f"    sqlite: {err}")
            print(f"    SQL:    {sql.replace(chr(10), ' ')[:140]}")

    if over_accepts and not args.summary_only:
        print("\nFirst SS-RA (sqlite rejects; we accept — review):")
        for loc, sql in over_accepts[:10]:
            print(f"  {loc}")
            print(f"    SQL: {sql.replace(chr(10), ' ')[:140]}")

    if bugs == 0:
        return 0
    if args.threshold is not None and total > 0:
        clean = (counts['SS-AA'] + counts['SS-RR'] + counts['SS-RA'] + allowlisted)
        rate = clean / total
        if rate >= args.threshold:
            print(f"\nclean rate {rate:.4f} >= threshold {args.threshold:.4f}; OK")
            return 0
        print(f"\nclean rate {rate:.4f} < threshold {args.threshold:.4f}; REGRESSION")
    return 1


if __name__ == "__main__":
    sys.exit(main())
