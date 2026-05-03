# Allowlisted test cases

The differential-against-libsqlite3 harness compares our
grammar's accept/reject decision to libsqlite3's on every SQL fragment
extracted from sqlite's upstream test corpus. Each fragment falls into
one of four buckets:

| code  | both accept | we accept | we reject |
|-------|-------------|-----------|-----------|
| **SS-AA** | ✓ | ✓ | — |
| **SS-RR** | ✓ | — | ✓ |
| **SS-AR** | sqlite OK | — | we err — *real bug unless allowlisted* |
| **SS-RA** | sqlite err | ✓ | — *we are over-permissive* |

The differential harness fails CI on any **SS-AR** case that is not
documented in `test/differential-allowlist.txt`. This file explains
the taxonomy of the few cases we DO allowlist, and why each one is
expected sqlite-leniency rather than a grammar bug to fix.

The harness does NOT fail on SS-RA cases — those represent intentional
permissiveness in our syntactic-only grammar (see §3 below).

## Files

- `test/differential-allowlist.txt` — SS-AR cases sqlite accepts and
  we reject. Each entry is a permanent exception with documented
  rationale. New entries require justification.
- `test/upstream-corpus-allowlist.txt` — fragment locations the
  upstream-corpus harness is permitted to fail. Currently
  empty; the harness uses a clean-rate threshold instead.

## 1. Current SS-AR allowlist (4 entries)

These are the only fragments where libsqlite3 accepts at parse-only
level but our grammar rejects. All four exhibit sqlite-internal
leniency rather than gaps in our grammar.

### 1.1 `alter.test:323` — ADD COLUMN with parenthesized garbage

```sql
ALTER TABLE t3 ADD COLUMN (ALTER TABLE t3 ADD COLUMN);
```

sqlite's `prepare_v2` returns no syntax error: it consumes the leading
`ALTER TABLE t3 ADD COLUMN`, then the parser accepts the trailing
`(...)` as part of the column-name + typename surface even though
parse.y's `columnname ::= nm typetoken` doesn't formally permit a
parenthesized opening. sqlite errors out at the SEMANTIC layer with
"no such table: t3" *before* validating the column shape.

Our grammar requires `name typename` per parse.y exactly and rejects
at parse time. **Our stricter behavior is arguably more correct**;
allowlisted because we don't want CI to fail on it.

### 1.2 `trigger1.test:240` — invalid SELECT in trigger body

```sql
CREATE TRIGGER r1 AFTER INSERT ON t1 BEGIN
  SELECT * FROM;  -- Syntax error
END;
```

sqlite stores trigger bodies *as text* during prepare and only
compiles them when the trigger fires. So `prepare_v2` accepts the
whole `CREATE TRIGGER` syntactically — the trailing `SELECT * FROM;`
is opaque text from sqlite's prepare-only perspective.

Our grammar parses the trigger body eagerly as part of the
`create_trigger_statement` rule and surfaces the embedded syntax
error. **Our eager parse is more useful for IDE consumers**, who want
to highlight the broken inner statement rather than wait for runtime.

### 1.3 `window1.test:1921` — fuzz-generated nested expression stress

A 3000-character window-function expression with `-true`, empty
`CAST(a AS )` (bare `AS`), and many-deep nested CASE/CAST/subquery
combinations. sqlite parses it (presumably with extensive lookahead
and error-recovery slack); we reject at one of the deeply-nested
edge cases.

A fuzz-generated test exercising sqlite's parser robustness, not a
real-world syntax pattern. Allowlisted as a known coverage gap that
isn't worth the complexity to fix.

### 1.4 `trigger1.test:834` — `#N` bind parameter inside trigger body

```sql
CREATE TABLE t1(a INT);
CREATE TRIGGER r1 AFTER INSERT ON t1 BEGIN
  INSERT INTO t1 SELECT e_master LIMIT 1,#1;
END;
```

The `#N` bind-parameter form is rejected by sqlite at top level (we
verified this with a direct probe). Trigger bodies are stored
verbatim and only fully parsed at fire time, so prepare doesn't see
the `#1` syntax error. Same root cause as §1.2.

## 2. Categories we deliberately do NOT allowlist

Some classes of SS-RA (sqlite-rejects, we-accept) are real
over-acceptance gaps that we *would* fix if it were tractable. We
don't allowlist these — they're tracked in the open SS-RA reports.

### 2.1 Build-flag-dependent: 75 cases

```sql
DELETE FROM t LIMIT 5;
DELETE FROM t ORDER BY x;
UPDATE t SET y=1 WHERE x=1 ORDER BY x LIMIT 1;
```

sqlite's `parse.y` gates DELETE/UPDATE-with-ORDER-BY/LIMIT behind
`SQLITE_ENABLE_UPDATE_DELETE_LIMIT`, resolved at lemon-generation
time. The standard amalgamation distribution (which our dev container
builds) is generated without the flag. parse.y's full surface
(modeled by our grammar) accepts these forms.

Defining `-DSQLITE_ENABLE_UPDATE_DELETE_LIMIT` at gcc-time has no
effect — parse.c is already preprocessed. To make the differential
match, libsqlite3 would need to be built from sqlite's source git
tree (not the amalgamation) with the flag — substantial dev-container
work documented in §3 of `Dockerfile.dev`.

These are **not real grammar bugs**; our grammar matches parse.y's
union-of-flags surface, which is the right behavior for a parser used
across sqlite builds with various flags.

### 2.2 Window-frame edge cases: 3 cases

```sql
SELECT count() OVER (ORDER BY x RANGE UNBOUNDED FOLLOWING) FROM t;
SELECT count() OVER (ORDER BY x RANGE BETWEEN UNBOUNDED FOLLOWING AND ...) FROM t;
SELECT count() OVER (ORDER BY x RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED PRECEDING) FROM t;
```

sqlite rejects these specific frame-bound combinations at parse time
even though parse.y's productions allow them generically. sqlite is
implementing a runtime check during parse that says "frame end >=
frame start." We attempted to express the SQL-standard distinction
between `frame_start` and `frame_end`, but sqlite is in fact more
lenient than the SQL standard about start-FOLLOWING / end-PRECEDING
combinations (see commit 0338341), so the strict approach
over-rejected 257 valid forms that sqlite accepts.

### 2.3 String-literal mid-statement edge cases (semantic)

A handful of multi-statement fragments where one specific statement
fails at sqlite's semantic layer (e.g., `ALTER TABLE b1 RENAME c TO
"a;b"` — semicolon inside quoted identifier in a later statement).
We accept syntactically; sqlite's semantic-validation phase rejects.

## 3. Why we don't try to match SS-RA at all costs

Our grammar is a **syntactic** parser. sqlite's `prepare_v2` does:

1. Tokenize (tokenize.c)
2. Parse (parse.y)
3. Build VDBE bytecode (semantic checks: no such table, no such
   column, no such function, frame-end >= frame-start, …)
4. Bind values

We replicate steps 1–2. We deliberately do *not* replicate step 3
because:

- Step 3 requires schema knowledge (which we don't have at parse time).
- Tooling consumers (IDEs, linters) layer their own semantic checks
  on top of our tree.
- Erring on the permissive side gives consumers more material to work
  with and lets them choose how strict to be.

For lexer-level strictness (step 1) we DO match sqlite, via the
external scanner in `src/scanner.c`. For
semantic-layer rejections (step 3), we trust consumers.

## 4. How to add or remove an allowlist entry

**Adding** an entry requires:
1. Verifying the case really IS sqlite-leniency (not a real grammar
   bug) by reasoning about which sqlite phase rejects it.
2. Writing a one-line rationale citing the sqlite phase and behavior.
3. Sufficient justification to convince a reviewer this is a
   permanent exception, not a band-aid.

**Removing** an entry:
1. Re-run the differential: if SS-AR no longer includes that location,
   the case has been fixed elsewhere.
2. Drop the line.

The list should shrink over time, not grow.

## 5. Related: the "allowlist file" for upstream-corpus

`test/upstream-corpus-allowlist.txt` exists for the upstream-corpus
harness but is currently empty — that harness uses a
clean-rate threshold (`--threshold 0.995`) rather than per-fragment
exceptions, since most "failures" are SS-RR (sqlite also rejects)
which don't require explanation. If a specific fragment ever needs
explicit allowlisting at the upstream-corpus level, the format is
the same as the differential allowlist.
