#!/usr/bin/env python3
"""Categorize SS-RA cases (sqlite rejects, we accept) by sqlite's
error message. Reads the dump produced by:

    scripts/run-differential.sh --dump-ss-ra build/ss-ra.tsv

and emits a categorized report grouped by error pattern + cause.

Categories:
  build-flag-dependent  ORDER BY / LIMIT in DELETE/UPDATE — gated by
                        SQLITE_ENABLE_UPDATE_DELETE_LIMIT at amalgamation
                        generation time. Our grammar models parse.y's
                        full surface; the standard amalgamation is built
                        without the flag.
  multi-statement       multi-stmt fragment where one specific
                        statement triggers the syntax error mid-way.
  semantic-strictness   sqlite's parser checks beyond pure syntax that
                        we don't replicate (window-frame keyword
                        positioning, etc.).
  malformed-token       lexer-level rejection that our scanner doesn't
                        catch (e.g. specific edge cases).
  other                 single-fragment edge cases.
"""

from __future__ import annotations
import re, sys
from pathlib import Path
from collections import Counter, defaultdict


def categorize(err: str, sql: str) -> str:
    e = err.lower()
    s = sql.lower()
    # Build-flag-dependent: ORDER BY / LIMIT in DELETE/UPDATE.
    if re.search(r'near "order": syntax error', e) and ('delete' in s or 'update' in s):
        return "build-flag-dependent (DELETE/UPDATE ORDER BY)"
    if re.search(r'near "limit": syntax error', e) and ('delete' in s or 'update' in s):
        return "build-flag-dependent (DELETE/UPDATE LIMIT)"
    # Window frame strictness.
    if 'near "following"' in e or 'near "preceding"' in e:
        return "window-frame strictness"
    # Lexer-level (number / string termination).
    if 'unrecognized token' in e:
        if re.search(r'unrecognized token: "[0-9]', e):
            return "malformed numeric (lexer)"
        if 'unrecognized token: "1.0e' in e:
            return "malformed scientific notation (lexer)"
        if "unrecognized token: \"');" in e or "unrecognized token: \"'" in e:
            return "string-literal termination edge case (multi-stmt)"
        if "unrecognized token: \"''')" in e:
            return "string-literal termination edge case (multi-stmt)"
        return "lexer-level (other)"
    # `near '` patterns inside multi-stmt — likely string termination.
    if "near \"');" in e or "near \"'" in e or "near \"''" in e:
        return "string-literal termination edge case (multi-stmt)"
    # Specific named tokens.
    if 'near "*":' in e:
        return "* in invalid position"
    if 'near "<=":' in e or 'near "b":' in e or 'near "i":' in e or \
       'near "it":' in e or 'near "does":' in e:
        return "single-fragment edge case"
    return "other"


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "build/ss-ra.tsv")
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 2

    by_category: defaultdict[str, list[tuple[str, str, str]]] = defaultdict(list)
    err_counts: Counter[str] = Counter()
    total = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        loc, err, sql = parts
        sql = sql.replace("\\n", " ").replace("\\t", " ").replace("\\\\", "\\")
        category = categorize(err, sql)
        by_category[category].append((loc, err, sql))
        err_counts[err.split("\\n", 1)[0][:60]] += 1
        total += 1

    print(f"# SS-RA categorized report — {total} cases")
    print()
    print("## By category")
    print()
    for cat, items in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
        print(f"### {cat}: {len(items)}")
        seen_locs = set()
        for loc, err, sql in items[:5]:
            if loc in seen_locs:
                continue
            seen_locs.add(loc)
            sql_one = sql[:140].strip()
            err_one = err.split("\\n", 1)[0][:80]
            print(f"- `{loc}`")
            print(f"  - sqlite: `{err_one}`")
            print(f"  - SQL: `{sql_one}`")
        if len(items) > 5:
            print(f"- ... and {len(items) - 5} more")
        print()

    print("## Top error messages (verbatim, by frequency)")
    print()
    for err, count in err_counts.most_common(15):
        print(f"- {count:>3}  `{err}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
