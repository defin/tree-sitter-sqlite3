## What

<!-- One paragraph: the construct or harness this PR changes. -->

## Why

<!--
Cite the upstream parse.y line numbers, sqlite test fixtures, or
sqlite-version specifics that justify the change. For grammar
changes, link the parse.y production you mirrored.
-->

## Test plan

- [ ] `tree-sitter test` — added / updated corpus fixture(s).
- [ ] `tree-sitter generate` — regenerated `src/`, committed.
- [ ] If `grammar.js` changed: `scripts/run-coverage.sh` still 100 %.
- [ ] If `scanner.c` changed: differential + roundtrip harnesses still green.
- [ ] If a new node type: a fixture exercises it (coverage harness).

## Notes

<!-- Allowlist additions need rationale per docs/allowlists.md. -->
