# Security policy

## Reporting a vulnerability

Report security issues via GitHub Security Advisories on this
repository, or by email to **defin@users.noreply.github.com** with
the subject prefix `[security]`.

Please **do not file a public issue** for vulnerabilities until a fix
is released or coordinated disclosure has happened.

We aim to acknowledge reports within **5 business days** and to ship
a fix within **30 days** for confirmed issues, faster for high-impact
crashes / arbitrary-code-execution surface.

## Scope

This is a tree-sitter grammar — a parser for SQL text. The runtime
attack surface is small but non-zero.

### In scope

- **Parser crashes / segfaults** on crafted SQL input via the
  external scanner (`src/scanner.c`) or the generated parser
  (`src/parser.c`). The scanner has manual byte-walking logic and
  is the highest-risk component.
- **Infinite loops / hangs** on crafted input.
- **Unbounded memory consumption** during parsing.
- **Tree corruption** (the parse tree disagrees with the input —
  ranges out of bounds, parent doesn't enclose children, etc.).
- **Identity-violating outputs** that could mislead a downstream
  security tool inspecting the parse tree (e.g. a query that
  contains `DROP TABLE` but where our tree omits it).

### Out of scope

- **sqlite itself.** Vulnerabilities in libsqlite3 should be
  reported upstream to the SQLite project at <https://sqlite.org/>.
- **Vendored upstream sources** under `vendor/`. These are unmodified
  copies of sqlite source files. Any vulnerability there is upstream's.
- **Downstream consumers** (IDEs, linters, etc. that use this parser).
  Their security posture is their responsibility; we provide a
  permissive-but-accurate syntactic tree.
- **Semantic vulnerabilities** ("this SQL is dangerous to execute")
  — out of scope because we don't model semantics. Downstream tools
  doing security analysis on parse trees implement their own checks.
- **The dev container** (`Dockerfile.dev`) — it's a development tool,
  not a production runtime.

## Disclosure policy

For confirmed in-scope vulnerabilities:

1. We acknowledge receipt and confirm scope.
2. We work on a fix; reporter is consulted on disclosure timing.
3. Fix is released; advisory published with reporter credit (unless
   anonymity is requested).
4. Coordinated disclosure window: **30 days** by default after a fix
   is available, negotiable.

## Hardening notes for production users

If you're embedding this parser in a security-sensitive context
(e.g. an SQL static-analysis tool that processes attacker-controlled
input):

- Run the parser with bounded resources (memory / time limits) —
  tree-sitter doesn't enforce these itself.
- Validate that the parse tree's root range equals
  `[0, len(input)]` before consuming the tree (the roundtrip
  property test enforces this on our corpus, but in production you
  may see novel inputs).
- For comments-as-trust-boundaries (e.g. SQL injection through
  comment markers), be aware the parser intentionally accepts
  unterminated `/* ... <EOF>` per sqlite's tokenize.c behavior.
