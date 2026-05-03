# vendor/

Vendored upstream sqlite source files. **Do not edit these in this
repository.** They are the source of truth for the grammar; edits
go to upstream sqlite, then this directory is re-fetched.

## What's here

| File | Upstream path | Purpose |
|------|---------------|---------|
| `parse.y` | `src/parse.y` | The Lemon grammar — productions, terminal/nonterminal names, `%fallback` declarations, operator precedence. The structural source of truth. |
| `tokenize.c` | `src/tokenize.c` | The hand-written sqlite lexer. Defines how input bytes become the `TK_*` tokens that `parse.y` consumes — character classes, identifier rules, numeric/string/blob literal forms, comment handling. The lexical source of truth. |
| `mkkeywordhash.c` | `tool/mkkeywordhash.c` | The canonical keyword list with each keyword's `mask` (which sqlite build flags include it) and `priority` (controls hash-chain ordering). This is the authoritative SQL keyword set we mirror in `grammar.js`. |
| `shell.c` | `src/shell.c.in` | The sqlite3 CLI tool's source (`.in` because the released `shell.c` is generated from it by tool/mkshellc.tcl). The canonical list of dot-commands lives in `do_meta_command()`; phase 5 of grammar.js mirrors that list. |

## Currently pinned

- **sqlite version:** `version-3.47.0` (release tag on the upstream
  sqlite git mirror at https://github.com/sqlite/sqlite)
- **parse.y SHA-256:** `fedaa79bae37d8adadb41becbe64b31795034ae6be58b910c91fc6741525103c`
- **tokenize.c SHA-256:** `99b221e7704982603c27d93266823bf5019c4a1857dbb6ce997a42bfd2d3997f`
- **mkkeywordhash.c SHA-256:** `88e9a1412ae4c52b1fa662953a5c7b714404d01be41868dd3b5e602ffe1f40e5`
- **shell.c SHA-256:** `4a3d0e98ea2638d9097a158dab89edfd875335bc428aa58ebe5f23cd2e532897` (from `src/shell.c.in`)
- **Fetched:** 2026-04-27

## Update runbook

When sqlite ships a new release we want to track:

```bash
TAG=version-3.NN.0   # the new release tag

curl -fsSL https://raw.githubusercontent.com/sqlite/sqlite/$TAG/src/parse.y \
  -o vendor/parse.y
curl -fsSL https://raw.githubusercontent.com/sqlite/sqlite/$TAG/src/tokenize.c \
  -o vendor/tokenize.c
curl -fsSL https://raw.githubusercontent.com/sqlite/sqlite/$TAG/tool/mkkeywordhash.c \
  -o vendor/mkkeywordhash.c
curl -fsSL https://raw.githubusercontent.com/sqlite/sqlite/$TAG/src/shell.c.in \
  -o vendor/shell.c

sha256sum vendor/parse.y vendor/tokenize.c vendor/mkkeywordhash.c vendor/shell.c
```

Then:

1. Update **Currently pinned** above with the new tag, all three
   sha256 values, and fetch date.
2. Diff each file — `git diff vendor/`. What to look for:
   - **`parse.y`**: new productions, new precedence (`%left/%right/%nonassoc`),
     new `%fallback` declarations, new `%token` types.
   - **`tokenize.c`**: changes to character classes (`IdChar`, etc.),
     changes to numeric/string/blob literal forms, comment-handling
     changes, new escape sequences in string literals.
   - **`mkkeywordhash.c`**: additions to the keyword list (look for
     new `addKeyword(...)` lines or table edits — the keyword set is
     near the top of the file). Each new keyword needs to be either
     reserved in `grammar.js` or added to a fallback group.
3. Mirror the changes in `grammar.js`.
4. Add test fixtures under `test/corpus/` covering the new syntax.
5. Run `tree-sitter generate && tree-sitter test` in the dev
   container. Resolve any newly-introduced conflicts.
6. Commit the updated `vendor/`, `grammar.js`, regenerated `src/`,
   and the new test fixtures together in a single commit titled
   `vendor: update sqlite to <TAG>`.

## Why we vendor instead of submodule

A git submodule pointing at the full sqlite source tree pulls in
~100MB of C source for a single ~2000-line grammar file we care
about. Copying the one file we need keeps the repo small and makes
"what version are we tracking" trivially auditable from the file
contents.

The cost is that updates are manual rather than automatic — but
sqlite ships infrequent enough that this is fine, and we want
intentional review on every grammar change anyway.

## License

The sqlite project dedicates these source files to the public
domain. See https://www.sqlite.org/copyright.html.
