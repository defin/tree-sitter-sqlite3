# tree-sitter-sqlite3

[![CI](https://github.com/defin/tree-sitter-sqlite3/actions/workflows/ci.yml/badge.svg)](https://github.com/defin/tree-sitter-sqlite3/actions/workflows/ci.yml)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](LICENSE)

A tree-sitter grammar for SQLite's SQL dialect plus the sqlite3 CLI
dot-commands. Translated from upstream
[`parse.y`](https://www.sqlite.org/src/file/src/parse.y) and
[`tokenize.c`](https://www.sqlite.org/src/file/src/tokenize.c) —
every production, precedence rule, and `%fallback` mirrored.

Tracks sqlite **3.47.0**. Bindings: c, go, node, python, rust, swift.

Validated on every push by **seven harnesses totalling ~80 000 SQL
inputs** — including a differential against libsqlite3 3.47.0 over
38 043 fragments extracted from sqlite's own `test/*.test`, plus
libFuzzer + ASAN. Zero unallowlisted "sqlite-accepts / we-reject"
divergences. See [Validation](#validation).

## Coverage

Full DML / DDL / CTEs (incl. recursive) / window functions /
compound SELECT / upsert / RETURNING / generated columns /
`STRICT` / `WITHOUT ROWID` / dot-commands / ATTACH / PRAGMA /
VACUUM / REINDEX / ANALYZE / EXPLAIN / SAVEPOINT / transactions.
sqlite 3.44+ syntax included (aggregate-arg `ORDER BY`,
`RIGHT`/`FULL JOIN`, `UPDATE FROM`, vector-form `SET (a,b)=(...)`,
`VACUUM INTO <expr>`, `NULLS FIRST/LAST`, `count(DISTINCT)`).

Queries: `highlights.scm`, `locals.scm`, `tags.scm`.

## Validation

CI runs seven harnesses on every push (~80 000 inputs total):

| harness | inputs | bar |
|---|---:|---|
| `tree-sitter test` (hand-written corpus) | 147 | 100 % |
| upstream-corpus (sqlite's own `test/*.test`) | 38 043 | ≥ 99.5 % |
| differential vs libsqlite3 3.47.0 | 38 043 | 0 unallowlisted SS-AR |
| grammar-coverage (every named node type hit) | 100 types | 100 % |
| snapshot regression (byte-exact s-exprs) | 147 | byte-exact |
| extras-placement (comments between every adjacent token pair) | 1 220 | 100 % |
| roundtrip property (range / leaf-concat / monotonicity) | 147 | 100 % |

Plus libFuzzer + ASAN on the parser `.so` and a mutation fuzzer
against libsqlite3.

An external scanner (`src/scanner.c`) handles lexer-level strictness
(malformed blob/numeric literals, number-fused-to-identifier).

## Scope

**Syntactic only.** Mirrors `tokenize.c` + `parse.y`, not the
semantic-validation layer that runs during
`sqlite3_prepare_v2`'s code-gen. ~78 inputs we accept get rejected
by sqlite at runtime (build-flag-dependent productions, parse-time
semantic checks); see [`docs/allowlists.md`](docs/allowlists.md)
for the taxonomy. Layer your own semantic checks on top.

## Build

Inside the dev container:

```bash
docker compose build
docker compose run --rm dev tree-sitter generate
docker compose run --rm dev tree-sitter test
```

Or with a host `tree-sitter-cli@0.25` and `parser.c` already
checked in: `tree-sitter test` works directly from a fresh clone.

## Upstream tracking

Vendored under `vendor/` with sha256 pins and an update runbook
([`vendor/README.md`](vendor/README.md)):

- `parse.y` — productions, precedence, `%fallback`.
- `tokenize.c` — character classes, literal forms, comments.
- `mkkeywordhash.c` — canonical keyword list + masks.
- `shell.c` — dot-command list (sourced separately from parse.y).

Update loop: bump vendor → diff parse.y → mirror in `grammar.js`
→ add fixtures → `tree-sitter generate` → commit `src/`.

## Translation notes

- **`%fallback`**: `_identifier` as `choice(identifier, ...keyword_tokens)`.
- **`%wildcard ANY`**: ambiguity resolved via `conflicts`.
- **`%ifdef SQLITE_OMIT_*`**: always parse the un-`OMIT` form.
- **Lemon semantic actions (C blocks)**: not translated; downstream
  consumers do semantic validation.

## License

CC0-1.0 (mirrors SQLite's public-domain stance). Vendored sqlite
sources under `vendor/` are themselves public-domain per
<https://www.sqlite.org/copyright.html>.
