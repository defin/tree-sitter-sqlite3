# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-02

Initial public release. Tracks upstream sqlite `version-3.47.0`.

### Grammar surface

- Full SQL grammar translated from sqlite's `parse.y` (LALR(1) Lemon)
  into tree-sitter's GLR DSL: DML, DDL (CREATE/ALTER/DROP for
  TABLE/INDEX/VIEW/TRIGGER/VIRTUAL), CTEs (incl. recursive), window
  functions, compound SELECT (UNION/INTERSECT/EXCEPT), upsert
  (`ON CONFLICT`), `RETURNING`, generated columns, `STRICT` tables,
  `WITHOUT ROWID`.
- sqlite-specific surface: dot-commands (sourced from `shell.c`),
  ATTACH/DETACH (URI mode), PRAGMA, VACUUM, REINDEX, ANALYZE, EXPLAIN,
  SAVEPOINT, transaction control.
- sqlite 3.44+ syntax: aggregate-arg `ORDER BY`, `RIGHT JOIN`,
  `FULL JOIN`, vector-form `SET (col1, col2) = (...)`,
  `UPDATE FROM`, `VACUUM INTO <expression>`,
  `INSERT/UPDATE/DELETE` target-`AS`-alias, `NULLS FIRST/LAST`,
  table-level `PRIMARY KEY(... AUTOINCREMENT)`, `count(DISTINCT)`
  bare-DISTINCT, table-level FK `[NOT] DEFERRABLE INITIALLY ...`.
- Reserved-keyword discipline matching parse.y's `%fallback ID` list.
- Identifier surface: bare `name`, `"quoted"`, `` `backtick` ``,
  `[bracket]`, `'single-quoted-as-identifier'` fallback, full
  Unicode-byte support (matches tokenize.c IdChar).
- External scanner (`src/scanner.c`) for lexer-level strictness:
  rejects malformed blob literals (`X'01001'`, `X'01020 100'`,
  `X'012g45'`), number-fused-to-identifier (`123abc`),
  underscore-misplaced numerics (`0xFFEF_`, `123__456`), and bad
  scientific notation (`1.0e`).

### Tree-sitter queries

- `queries/highlights.scm`, `queries/locals.scm`, `queries/tags.scm`.

### Bindings

- C, Go, Node, Python, Rust, Swift.

### Vendored upstream

- `vendor/parse.y`, `vendor/tokenize.c`, `vendor/mkkeywordhash.c`,
  `vendor/shell.c` with sha256 pinning and an update runbook in
  `vendor/README.md`.

### Dev container

- `Dockerfile.dev` + `docker-compose.yml` providing node +
  tree-sitter-cli + python + rust toolchains.
- libsqlite3 3.47.0 built from the upstream amalgamation for the
  differential harness.

### CI: seven validation harnesses

- **`tree-sitter test`** — hand-written corpus (147 fixtures, 100 %).
- **`upstream-corpus`** — parses every SQL fragment extracted from
  sqlite's `test/*.test` files (~38 000 fragments, 99.5 %+).
- **`differential vs libsqlite3`** — runs the same fragments through
  both libsqlite3 3.47.0 and our parser, reports 4-way agreement
  matrix; CI fails on any non-allowlisted SS-AR (sqlite accepts, we
  reject). Currently 0.
- **`grammar-coverage`** — every named node type must be exercised by
  at least one input across the combined corpus (100 %).
- **`snapshot regression`** — byte-exact s-expression compare across
  147 curated inputs.
- **`extras-placement`** — splices `--` and `/* */` comments between
  every pair of adjacent tokens in the snapshot set, asserts
  parse-success and tree-shape invariance (1 220 variants, 100 %).
- **`roundtrip property`** — root range covers full input, leaf
  concatenation reproduces input byte-for-byte, sibling ranges
  weakly monotonic (147, 100 %).
- Plus per-OS build smoke tests for node / python / rust / go
  bindings on Ubuntu / macOS / Windows.

### Documentation

- `docs/allowlists.md` — taxonomy of the 4 SS-AR cases where sqlite
  is more lenient than parse.y, and the 78 SS-RA over-acceptance
  cases (build-flag-dependent productions and sqlite's parse-time
  semantic checks).

[Unreleased]: https://github.com/defin/tree-sitter-sqlite3/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/defin/tree-sitter-sqlite3/releases/tag/v0.1.0
