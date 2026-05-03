---
name: Bug report
about: Report a parse failure, wrong tree shape, crash, or build issue
title: ""
labels: bug
assignees: ""
---

## What happened

<!-- One sentence: what did you see vs. what did you expect. -->

## Minimal reproducer

<!--
The smallest SQL input (or build command) that triggers it. Paste it
verbatim — do not paraphrase. If the input is generated, give the
generator. If reproducing requires a particular grammar build,
include the commit SHA.
-->

```sql
-- paste here
```

## Observed parse tree (or error)

<!--
Output of `tree-sitter parse <file>` (or the relevant binding's
equivalent), or the build/compile error verbatim.
-->

```
```

## Expected parse tree (or behaviour)

<!--
Either a hand-written sexp showing the shape you expected, or a
reference to the matching upstream sqlite parse.y production.
-->

## Environment

- Grammar commit / version:
- tree-sitter-cli version:
- Binding (node / python / rust / go / swift / c) and its version:
- OS / arch:

## Anything else

<!-- Allowlist entry candidate? Differential SS-AR? Snapshot diff attached? -->
