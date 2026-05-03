# Contributing to tree-sitter-sqlite3

Thanks for your interest. This is a long-term, permanently-maintained
artifact tracking a specific upstream sqlite release. The contribution
norms below reflect that.

## Source of truth

The grammar is a translation of upstream sqlite's `parse.y` and
`tokenize.c`, pinned to a specific release tag. The vendored copies
live under `vendor/`:

- **`vendor/parse.y`** — the Lemon grammar (productions, precedence,
  `%fallback`).
- **`vendor/tokenize.c`** — the hand-written sqlite lexer.
- **`vendor/mkkeywordhash.c`** — the canonical SQL keyword list.
- **`vendor/shell.c`** — the sqlite3 CLI source for dot-commands.

**Do not edit the files in `vendor/` directly.** They are upstream
content, fetched at the version pinned in `vendor/README.md`. Updates
go through the runbook in that file.

When upstream sqlite ships a new release we want to track:

1. Re-fetch the four vendored files at the new tag, update
   `vendor/README.md`'s sha256s + tag.
2. Diff old vs new `parse.y` to find what changed.
3. Mirror production / precedence / fallback changes in `grammar.js`.
4. Add corpus fixtures under `test/corpus/` covering new syntax.
5. Re-generate via `tree-sitter generate`, commit `src/`.

## The dev container is the canonical build path

Build, test, and validate everything inside the dev container:

```bash
docker compose build
docker compose run --rm dev tree-sitter generate
docker compose run --rm dev tree-sitter test
docker compose run --rm dev pip install -e . --break-system-packages
```

The container has the exact tree-sitter-cli version pinned to match
`Cargo.toml` / `pyproject.toml` peer-dep ranges, plus
libsqlite3 3.47.0 built to match the version pinned in
`vendor/README.md`. Building outside the container risks
version-skew bugs that won't reproduce in CI.

## After every grammar.js edit

```bash
docker compose run --rm dev tree-sitter generate    # regenerates src/
docker compose run --rm dev tree-sitter test        # runs corpus
```

**Commit `src/grammar.json`, `src/parser.c`, and
`src/node-types.json` along with your `grammar.js` change.** They are
generated, but checked in so consumers don't need
`tree-sitter-cli` to build. CI verifies they're up-to-date.

If you change `src/scanner.c` (the external scanner), also commit
that. CI compiles it for every binding.

## Test discipline

This repo runs **seven validation harnesses** on every push. New
contributions must keep all of them green.

### 1. Hand-written corpus (`test/corpus/*.txt`)

Add a fixture for any new grammar feature. Format:

```
==============================================
test name
==============================================

<SQL input>

---

<expected s-expression>
```

Run with `tree-sitter test`. CI requires 100 %.

### 2. Upstream-corpus harness (`scripts/run-upstream-corpus.sh`)

Parses every SQL fragment from sqlite's `test/*.test`. New grammar
features should bring the pass rate UP, not down. Threshold currently
0.995 — drops below fail CI.

### 3. Differential vs libsqlite3 (`scripts/run-differential.sh`)

Compares accept/reject decisions to libsqlite3 3.47.0. CI fails on
any unallowlisted **SS-AR** (sqlite accepts, we reject — real grammar
bug). See [`docs/allowlists.md`](docs/allowlists.md) for the
allowlist policy: entries shrink over time, never grow.

### 4. Grammar coverage (`scripts/run-coverage.sh`)

Every named node type must be hit by at least one input across the
combined corpus. Threshold 1.0. **If you add a new rule, add a
fixture that exercises it** — coverage will fail otherwise.

### 5. Snapshot regression (`scripts/run-snapshots.sh`)

Byte-exact s-expression compare. After an INTENTIONAL grammar change
that affects tree shape, regenerate snapshots:

```bash
docker compose run --rm dev python3 scripts/snapshot-test.py --update
git add test/snapshots/
git commit -m "snapshots: refresh after <grammar change>"
```

Don't blindly update snapshots without understanding the diff.

### 6. Extras-placement matrix (`scripts/run-extras-placement.sh`)

Splices `--` and `/* */` comments between every pair of adjacent
tokens. Token rules that swallow surrounding whitespace will fail
this. CI threshold 100 %.

### 7. Roundtrip property tests (`scripts/run-roundtrip.sh`)

Asserts the parse tree's root range covers the entire input, that
leaf concatenation reproduces the input byte-for-byte, and that
sibling ranges are weakly monotonic. Anonymous tokens that get
inlined out of leaf walks will fail this. Use NAMED rules for any
non-trivial token spans you want preserved in the tree (see e.g.
`dot_command_arguments`, `vtab_module_arg`).

## Allowlist additions need justification

`test/differential-allowlist.txt` documents cases where sqlite
accepts but we reject. **Adding an entry requires a one-line
rationale identifying which sqlite phase rejects** (lexer, parser,
codegen). See [`docs/allowlists.md`](docs/allowlists.md).

The list should shrink over time, not grow. Don't allowlist a real
grammar bug — fix it.

## Commit message style

Look at `git log --oneline` for the convention. In short:

- Subject line: lowercase, imperative, ≤ 72 chars.
- For grammar changes: prefix with `grammar:`.
- For test/harness changes: prefix with `test/<harness>:`.
- For CI changes: prefix with `ci:`.
- Body explains *why* the change is correct, citing parse.y line
  numbers, sqlite test fixtures, or sqlite-version specifics.

No DCO or CLA. Standard GitHub PR flow.

## What this repo will NOT accept

- **Edits to `vendor/`**. Upstream-only.
- **Grammar changes that drop tests**. Add fixtures, don't remove.
- **Allowlist entries without rationale**. See above.
- **`grammar.js` changes without regenerating `src/`**. CI catches
  this.

## Reporting bugs

File an issue with:

- The exact input SQL.
- The actual parse tree (`tree-sitter parse <file>`).
- The expected behavior (with reference to parse.y / sqlite docs if
  the bug is grammar-correctness).

For security issues, see [`SECURITY.md`](SECURITY.md).
