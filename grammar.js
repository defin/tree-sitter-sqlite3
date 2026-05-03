/**
 * @file SQLite3 grammar for tree-sitter
 * @license CC0-1.0
 *
 * Translated from sqlite's parse.y (Lemon LALR(1)) and tokenize.c
 * (hand-written lexer), pinned in vendor/. See README.md and
 * vendor/README.md for the source-of-truth process.
 */

/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

// --- Helpers -----------------------------------------------------------------

/**
 * Case-insensitive keyword. SQL keywords are case-insensitive
 * (`select` == `SELECT` == `SeLeCt`); tree-sitter literal tokens are
 * case-sensitive, so we generate a regex per keyword.
 */
function kw(word) {
  const pat = word.split("").map((c) =>
    /[A-Za-z]/.test(c)
      ? `[${c.toUpperCase()}${c.toLowerCase()}]`
      : c.replace(/[\\^$.|?*+()[\]{}]/g, "\\$&")
  ).join("");
  return new RegExp(pat);
}

/** Comma-separated list of `rule`, with at least one element. */
function commaSep1(rule) {
  return seq(rule, repeat(seq(",", rule)));
}

// --- Operator precedence (parse.y lines 289-301) -----------------------------

const PREC = {
  OR: 1,
  AND: 2,
  NOT: 3,
  COMPARE: 4,    // IS MATCH LIKE_KW BETWEEN IN ISNULL NOTNULL NE EQ
  ORDER: 5,      // GT LE LT GE
  ESCAPE: 6,
  BITWISE: 7,    // BITAND BITOR LSHIFT RSHIFT
  ADD: 8,        // PLUS MINUS
  MUL: 9,        // STAR SLASH REM
  CONCAT: 10,    // CONCAT PTR (string concat / JSON ->/->>)
  COLLATE: 11,
  UNARY: 12,     // BITNOT (and unary minus/plus)
  ON: 13,
};

// =============================================================================

module.exports = grammar({
  name: "sqlite3",

  extras: ($) => [
    /[ \t\r\n]/,
    $.line_comment,
    $.block_comment,
  ],

  word: ($) => $.identifier,

  // External scanner (src/scanner.c): handles strict-tokenization
  // edge cases that the regex-based lexer cannot reject. Emits
  // distinct visible tokens so consumers (IDEs, linters) can detect
  // the malformed input and flag it as an error. Our differential
  // and upstream-corpus harnesses both treat these node types as
  // parse failures, mirroring sqlite tokenize.c's behavior.
  externals: ($) => [
    $.malformed_blob_literal,    // X'<bad>' — odd length, non-hex, etc.
    $.malformed_number_id,       // 123abc — number directly fused to id
  ],

  // Global reserved-word set. Tokens listed here will NOT fall back
  // to identifier even when no other rule consumes the keyword token
  // in the current parse state. This mirrors parse.y's strict-keyword
  // policy: only keywords NOT in parse.y's `%fallback ID` list are
  // reserved. Keywords IN the fallback list (BEGIN, END, RENAME,
  // STRICT, TRIGGER, FILTER, BY, IF, etc.) can be used as identifiers
  // and so are deliberately omitted here.
  reserved: {
    sql: ($) => [
      // Statement-keyword core
      kw("select"), kw("insert"), kw("update"), kw("delete"),
      kw("create"), kw("alter"), kw("drop"), kw("add"),
      // Clause-keyword core
      kw("from"), kw("where"), kw("group"), kw("having"),
      kw("order"), kw("limit"), kw("into"), kw("values"),
      kw("set"), kw("on"), kw("as"), kw("using"),
      kw("returning"),
      // Logic / comparison / sentinel
      kw("and"), kw("or"), kw("not"), kw("null"),
      kw("is"), kw("in"), kw("between"),
      kw("isnull"), kw("notnull"), kw("exists"),
      // Control-flow expressions
      kw("then"), kw("else"), kw("when"), kw("case"),
      kw("escape"),
      // Set operators (only fallback if SQLITE_OMIT_COMPOUND_SELECT,
      // which we don't define — so these stay reserved).
      kw("union"), kw("intersect"), kw("except"),
      // Function-arg modifiers
      kw("all"), kw("distinct"),
      // Constraints
      kw("constraint"), kw("primary"), kw("unique"),
      kw("check"), kw("foreign"), kw("references"),
      kw("default"), kw("collate"), kw("autoincrement"),
      // DDL targets
      kw("table"), kw("index"),
      // Transactions (BEGIN, ROLLBACK, RELEASE, SAVEPOINT, TRANSACTION
      // are all in fallback; only COMMIT here per parse.y).
      kw("commit"),
    ],
  },

  conflicts: ($) => [
    // `... JOIN b ON x = 1 ON CONFLICT ...` — the parser must
    // disambiguate "consume the ON as a join constraint" vs
    // "close the join_step (no constraint), start an upsert_clause".
    // The same surface ambiguity is documented in parse.y line 819.
    // GLR explores both paths; the longer constraint-consuming parse
    // wins where the two reconverge.
    [$.join_step],
    // `INSERT INTO t VALUES(...)` is ambiguous with INSERT...SELECT
    // when _select_compound's _select_or_values branch can match the
    // VALUES form. parse.y treats INSERT-VALUES and INSERT-SELECT as
    // separate productions; we give the direct values_clause branch
    // a higher dynamic precedence in insert_statement to resolve this.
    [$.insert_statement, $._select_or_values],
    // After a single FROM table reference, `ON x = 1` could be either
    // a join constraint (now allowed even for the first table in
    // seltablist) or the start of `ON CONFLICT` for an upsert. The
    // GLR parser explores both; the longer ON-CONFLICT match wins
    // in INSERT context, the join-constraint shape applies in SELECT.
    [$._join_clause],
    // `SELECT a window` is ambiguous between (a, alias=window) and
    // (a, then WINDOW clause). Tree-sitter explores both and picks
    // the longer match (WINDOW clause if a window-definition follows).
    [$.expression_result_column],
    // `(SELECT ...)` is ambiguous between a parenthesized compound
    // operand and a scalar subquery_expression. GLR explores both;
    // the compound-operand interpretation wins when followed by a
    // compound operator (UNION/EXCEPT/INTERSECT), the
    // subquery_expression wins where an expression is expected.
    [$._select_or_values, $.subquery_expression],
    // dot_command at end-of-input: ambiguous between "final
    // statement" and "non-final statement" with an implicit
    // newline-terminator. Both produce equivalent trees.
    [$.source_file],
    // Same shape, table_or_subquery position: `(SELECT ...)` could
    // be the FROM-source subquery, OR a compound operand.
    [$._select_or_values, $.table_or_subquery],
    // `FROM t window` — table alias `window` vs WINDOW-clause start.
    [$.table_or_subquery],
    // `f() over` — `over name` window reference vs name as alias.
    [$.function_call],
    // `CONSTRAINT one CONSTRAINT two PRIMARY KEY(a)` — the leading
    // CONSTRAINT NAME could be either a bare-name constraint
    // followed by another, or the prefix of the FULL constraint that
    // contains the body. GLR explores both; the longer match (full
    // constraint) wins where one exists. Same shape applies at both
    // table-level and column-level.
    [$.table_constraint],
    [$.column_constraint],
  ],

  rules: {
    // -------------------- Top level --------------------

    // parse.y `cmdlist` rule: cmd-list is a sequence where each command
    // may be followed by a `;` separator. Only the LAST command may
    // omit the `;` (parse.y `ecmd ::= cmdx SEMI`). Modeling it that
    // way avoids ambiguity between schema-qualified names and the
    // start of a dot-command (e.g. `SELECT * FROM main.users` could
    // otherwise be misparsed as `SELECT * FROM main` + dot-command
    // `.users` if any statement could end without `;`).
    //
    // Empty statements (`;`) are allowed (parse.y `ecmd ::= SEMI`),
    // so `SELECT 1;;` and a leading-`;` input both parse cleanly.
    // Dot-commands self-terminate at newline (their args token
    // matches up to the newline) — they do NOT require a trailing
    // `;` and may be freely interleaved with SQL statements.
    source_file: ($) =>
      seq(
        repeat(";"),
        repeat(choice(
          $.dot_command,
          seq($._statement, repeat1(";")),
        )),
        optional(choice($.dot_command, $._statement)),
      ),

    _statement: ($) =>
      choice(
        $.select_statement,
        $.insert_statement,
        $.update_statement,
        $.delete_statement,
        $.create_table_statement,
        $.create_index_statement,
        $.create_view_statement,
        $.create_trigger_statement,
        $.create_virtual_table_statement,
        $.alter_table_statement,
        $.drop_table_statement,
        $.drop_index_statement,
        $.drop_view_statement,
        $.drop_trigger_statement,
        $.attach_statement,
        $.detach_statement,
        $.pragma_statement,
        $.vacuum_statement,
        $.reindex_statement,
        $.analyze_statement,
        $.explain_statement,
        $.begin_statement,
        $.commit_statement,
        $.rollback_statement,
        $.savepoint_statement,
        $.release_statement,
      ),

    // -------------------- INSERT (parse.y lines 1024-1071) --------------------
    //
    // cmd ::= with insert_cmd INTO xfullname idlist_opt select upsert
    // cmd ::= with insert_cmd INTO xfullname idlist_opt DEFAULT VALUES returning
    // insert_cmd ::= INSERT orconf | REPLACE
    // orconf ::= empty | OR resolvetype
    // resolvetype ::= ROLLBACK | ABORT | FAIL | IGNORE | REPLACE
    //
    // Covers: INSERT|REPLACE INTO target [(cols)]
    //         (VALUES rows | SELECT | DEFAULT VALUES)
    //         [ON CONFLICT ...] [RETURNING ...] ;
    insert_statement: ($) =>
      seq(
        optional(field("with", $.with_clause)),
        field(
          "kind",
          choice(
            seq(
              alias(kw("insert"), "INSERT"),
              optional(seq(
                alias(kw("or"), "OR"),
                field("conflict_resolution", $._resolve_type),
              )),
            ),
            alias(kw("replace"), "REPLACE"),
          ),
        ),
        alias(kw("into"), "INTO"),
        field("target", $.qualified_table_name),
        // parse.y `xfullname ::= nm DOT nm AS nm`: INSERT target may
        // carry an AS alias used to disambiguate column references in
        // ON CONFLICT DO UPDATE / RETURNING clauses (upsert2.test).
        optional(seq(
          optional(alias(kw("as"), "AS")),
          field("alias", $._id),
        )),
        optional(seq(
          "(",
          field("columns", $.column_name_list),
          ")",
        )),
        field(
          "source",
          choice(
            // Direct VALUES gets higher precedence than the
            // _select_compound branch (which now also accepts a
            // leading values_clause via _select_or_values). parse.y
            // distinguishes INSERT...VALUES from INSERT...SELECT as
            // separate productions; we mirror that disambiguation.
            prec(1, $.values_clause),
            $.default_values_clause,
            alias($._select_compound, $.select_clause),
          ),
        ),
        repeat(field("upsert", $.upsert_clause)),
        optional(field("returning", $.returning_clause)),
      ),

    // -------------------- Upsert (ON CONFLICT) (parse.y lines 1042-1052) --------------------
    upsert_clause: ($) =>
      seq(
        alias(kw("on"), "ON"),
        alias(kw("conflict"), "CONFLICT"),
        optional(seq(
          "(",
          commaSep1(field("target_column", $.indexed_column)),
          ")",
          optional(field("target_where", $.where_clause)),
        )),
        alias(kw("do"), "DO"),
        choice(
          alias(kw("nothing"), "NOTHING"),
          seq(
            alias(kw("update"), "UPDATE"),
            alias(kw("set"), "SET"),
            commaSep1(field("assignment", $.set_assignment)),
            optional(field("where", $.where_clause)),
          ),
        ),
      ),

    // -------------------- RETURNING (parse.y line 1054) --------------------
    returning_clause: ($) =>
      seq(
        alias(kw("returning"), "RETURNING"),
        $.result_column_list,
      ),

    _resolve_type: ($) =>
      choice(
        alias(kw("rollback"), "ROLLBACK"),
        alias(kw("abort"), "ABORT"),
        alias(kw("fail"), "FAIL"),
        alias(kw("ignore"), "IGNORE"),
        alias(kw("replace"), "REPLACE"),
      ),

    // VALUES (...) [, (...)]* — parse.y `values` + `mvalues` rules.
    values_clause: ($) =>
      seq(
        alias(kw("values"), "VALUES"),
        commaSep1(seq("(", commaSep1(field("value", $._expression)), ")")),
      ),

    // DEFAULT VALUES — parse.y line 1030.
    default_values_clause: ($) =>
      seq(
        alias(kw("default"), "DEFAULT"),
        alias(kw("values"), "VALUES"),
      ),

    column_name_list: ($) => commaSep1(field("column", $._id)),

    // -------------------- UPDATE (parse.y lines 957-1022) --------------------
    //
    // cmd ::= with UPDATE orconf xfullname indexed_opt SET setlist from
    //         where_opt_ret orderby_opt limit_opt
    //
    // Covers: UPDATE [OR conflict-action] target [INDEXED BY name]
    //         SET assignments [WHERE expr]
    //                  [ORDER BY orderlist] [LIMIT N [OFFSET M]] ;
    //
    // parse.y `cmd ::= with UPDATE orconf xfullname indexed_opt SET
    //                   setlist from where_opt_ret orderby_opt limit_opt`.
    // The FROM clause is the sqlite UPDATE-FROM extension (added in
    // 3.33). It uses the same join-clause shape as SELECT's FROM.
    update_statement: ($) =>
      seq(
        optional(field("with", $.with_clause)),
        alias(kw("update"), "UPDATE"),
        optional(seq(
          alias(kw("or"), "OR"),
          field("conflict_resolution", $._resolve_type),
        )),
        field("target", $.qualified_table_name),
        // parse.y `xfullname ::= nm DOT nm AS nm`: UPDATE target may
        // carry an AS alias used so subqueries in WHERE / RETURNING
        // can refer to the outer row (update.test:512).
        optional(seq(
          optional(alias(kw("as"), "AS")),
          field("alias", $._id),
        )),
        optional($._indexed_by_clause),
        alias(kw("set"), "SET"),
        commaSep1(field("assignment", $.set_assignment)),
        optional(field("from", $.from_clause)),
        optional(field("where", $.where_clause)),
        optional(field("returning", $.returning_clause)),
        optional(field("order_by", $.order_by_clause)),
        optional(field("limit", $.limit_clause)),
      ),

    // parse.y `setlist`:
    //   setlist ::= setlist COMMA nm EQ expr
    //   setlist ::= setlist COMMA LP idlist RP EQ expr
    //   setlist ::= nm EQ expr
    //   setlist ::= LP idlist RP EQ expr
    // Two forms — single-column `col = expr` and the vector form
    // `(col1, col2, ...) = expr` where the RHS is typically a
    // parenthesized expression-list or a row-returning subquery.
    set_assignment: ($) =>
      seq(
        choice(
          field("column", $._id),
          seq(
            "(",
            commaSep1(field("column", $._id)),
            ")",
          ),
        ),
        // sqlite's EQ token-class accepts both `=` and `==`.
        choice("=", "=="),
        field("value", $._expression),
      ),

    _indexed_by_clause: ($) =>
      choice(
        seq(alias(kw("indexed"), "INDEXED"), alias(kw("by"), "BY"), $._id),
        seq(alias(kw("not"), "NOT"), alias(kw("indexed"), "INDEXED")),
      ),

    where_clause: ($) =>
      seq(alias(kw("where"), "WHERE"), $._expression),

    order_by_clause: ($) =>
      seq(
        alias(kw("order"), "ORDER"),
        alias(kw("by"), "BY"),
        commaSep1($.order_term),
      ),

    // parse.y `sortlist` rule: `expr [ASC|DESC] [NULLS FIRST|NULLS LAST]`.
    // NULLS FIRST/LAST was added in sqlite 3.30.
    order_term: ($) =>
      seq(
        $._expression,
        optional(choice(
          alias(kw("asc"), "ASC"),
          alias(kw("desc"), "DESC"),
        )),
        optional(seq(
          alias(kw("nulls"), "NULLS"),
          choice(
            alias(kw("first"), "FIRST"),
            alias(kw("last"), "LAST"),
          ),
        )),
      ),

    limit_clause: ($) =>
      seq(
        alias(kw("limit"), "LIMIT"),
        $._expression,
        optional(seq(
          choice(alias(kw("offset"), "OFFSET"), ","),
          $._expression,
        )),
      ),

    // -------------------- SELECT (parse.y lines 570-690) --------------------
    //
    // The full SELECT grammar in parse.y is large — joins, compound
    // SELECT (UNION/INTERSECT/EXCEPT), CTEs (WITH RECURSIVE), window
    // functions, subqueries, table-valued functions, all covered.
    //
    // oneselect ::= SELECT distinct selcollist from where_opt
    //               groupby_opt having_opt orderby_opt limit_opt
    //
    // Core form:
    //   SELECT [DISTINCT|ALL] result-column-list
    //   [FROM qualified-table [AS? alias]]
    //   [WHERE expr]
    //   [GROUP BY expr-list [HAVING expr]]
    //   [ORDER BY order-term-list]
    //   [LIMIT expr [OFFSET expr | , expr]]
    //   ;
    select_statement: ($) => $._select_compound,

    // -------------------- CTE (parse.y lines 1849-1865) --------------------
    //
    // with ::= WITH wqlist | WITH RECURSIVE wqlist
    // wqitem ::= name [(col-list)] AS [NOT MATERIALIZED|MATERIALIZED] (select)
    with_clause: ($) =>
      seq(
        alias(kw("with"), "WITH"),
        optional(field("recursive", alias(kw("recursive"), "RECURSIVE"))),
        commaSep1(field("cte", $.cte_definition)),
      ),

    cte_definition: ($) =>
      seq(
        field("name", $._id),
        optional(seq(
          "(",
          commaSep1(field("column", $._id)),
          ")",
        )),
        alias(kw("as"), "AS"),
        optional(field("materialization", choice(
          alias(kw("materialized"), "MATERIALIZED"),
          seq(alias(kw("not"), "NOT"), alias(kw("materialized"), "MATERIALIZED")),
        ))),
        "(",
        field("body", alias($._select_compound, $.select_clause)),
        ")",
      ),

    // -------------------- Compound SELECT (parse.y lines 582-610) --------------------
    //
    // selectnowith ::= oneselect | selectnowith multiselect_op oneselect
    // multiselect_op ::= UNION | UNION ALL | EXCEPT | INTERSECT
    // parse.y `select ::= WITH wqlist selectnowith | selectnowith`:
    // a compound select may have a leading WITH clause. Modeling it
    // here means every consumer of _select_compound (top-level select,
    // CTE body, view body, scalar subquery, INSERT-from-SELECT, etc.)
    // gets WITH support uniformly.
    //
    // parse.y `oneselect ::= SELECT ... | values`: a `oneselect` can
    // be either a SELECT statement or a VALUES clause. CTEs and
    // subqueries in particular often use the VALUES form.
    _select_compound: ($) =>
      seq(
        optional(field("with", $.with_clause)),
        $._select_or_values,
        repeat(seq(
          field("compound_operator", $._compound_operator),
          $._select_or_values,
        )),
      ),

    // parse.y `oneselect ::= LP select RP`: a compound-select operand
    // may itself be wrapped in parens (allows nesting compounds with
    // explicit precedence, e.g. `(A UNION B) EXCEPT C`).
    _select_or_values: ($) => choice(
      $._select_core,
      $.values_clause,
      seq("(", alias($._select_compound, $.select_clause), ")"),
    ),

    _compound_operator: ($) =>
      choice(
        seq(
          alias(kw("union"), "UNION"),
          optional(alias(kw("all"), "ALL")),
        ),
        alias(kw("intersect"), "INTERSECT"),
        alias(kw("except"), "EXCEPT"),
      ),

    _select_core: ($) =>
      seq(
        alias(kw("select"), "SELECT"),
        optional(field("modifier", choice(
          alias(kw("distinct"), "DISTINCT"),
          alias(kw("all"), "ALL"),
        ))),
        field("columns", $.result_column_list),
        optional(field("from", $.from_clause)),
        optional(field("where", $.where_clause)),
        optional(field("group_by", $.group_by_clause)),
        optional(field("having", $.having_clause)),
        optional(field("window", $.window_clause)),
        optional(field("order_by", $.order_by_clause)),
        optional(field("limit", $.limit_clause)),
      ),

    // Named window clause: WINDOW w1 AS (...), w2 AS (...).
    // parse.y windowdefn_list, line 1879.
    window_clause: ($) =>
      seq(
        alias(kw("window"), "WINDOW"),
        commaSep1($.named_window),
      ),

    named_window: ($) =>
      seq(
        field("name", $._id),
        alias(kw("as"), "AS"),
        "(",
        // Empty window definition `()` is valid (window1.test:1312).
        optional($.window_definition),
        ")",
      ),

    result_column_list: ($) =>
      commaSep1($._result_column),

    _result_column: ($) =>
      choice(
        $.star_result_column,
        $.qualified_star_result_column,
        $.expression_result_column,
      ),

    star_result_column: ($) => "*",

    qualified_star_result_column: ($) =>
      seq(field("table", $._id), ".", "*"),

    expression_result_column: ($) =>
      seq(
        field("expression", $._expression),
        optional(seq(
          optional(alias(kw("as"), "AS")),
          field("alias", $._id),
        )),
      ),

    // FROM clause: a sequence of table sources joined by COMMA or
    // explicit JOIN keywords. parse.y `from ::= FROM seltablist`
    // composes via `stl_prefix` (lines 719-808).
    from_clause: ($) =>
      seq(
        alias(kw("from"), "FROM"),
        $._join_clause,
      ),

    // The FROM body: either a single table source, or a chain of
    // table sources connected by joinop with optional ON/USING. We
    // model this left-recursively via _join_clause/join_step so the
    // resulting tree mirrors how parse.y's stl_prefix accumulates.
    // parse.y `seltablist ::= nm AS nm on_using_opt`: even the FIRST
    // table in seltablist may carry an ON/USING constraint (sqlite
    // accepts and silently ignores it for a non-join, see tkt3935).
    _join_clause: ($) =>
      seq(
        field("source", $.table_or_subquery),
        optional(field("constraint", $._join_constraint)),
        repeat(field("join", $.join_step)),
      ),

    join_step: ($) =>
      seq(
        field("operator", $._join_operator),
        field("source", $.table_or_subquery),
        optional(field("constraint", $._join_constraint)),
      ),

    // parse.y line 811-816:
    //   joinop ::= COMMA | JOIN
    //            | JOIN_KW JOIN
    //            | JOIN_KW nm JOIN
    //            | JOIN_KW nm nm JOIN
    // JOIN_KW per mkkeywordhash.c: CROSS, FULL, INNER, LEFT, NATURAL,
    // OUTER, RIGHT. The `nm`/`nm nm` forms allow arbitrary identifiers
    // between the join-keyword and JOIN — sqlite parses (and ignores)
    // them as decorations, e.g. `LEFT BOGUS JOIN`, `NATURAL AWK SED
    // JOIN` (join.test:363+).
    _join_operator: ($) =>
      choice(
        ",",
        alias(kw("join"), "JOIN"),
        seq(
          repeat1(choice(
            alias(kw("cross"), "CROSS"),
            alias(kw("full"), "FULL"),
            alias(kw("inner"), "INNER"),
            alias(kw("left"), "LEFT"),
            alias(kw("natural"), "NATURAL"),
            alias(kw("outer"), "OUTER"),
            alias(kw("right"), "RIGHT"),
          )),
          // Up to two arbitrary identifier "decorations" between the
          // join-kind keyword(s) and JOIN.
          optional(field("decoration", $._id)),
          optional(field("decoration", $._id)),
          alias(kw("join"), "JOIN"),
        ),
      ),

    // ON expr | USING (col-list)
    _join_constraint: ($) =>
      choice(
        seq(alias(kw("on"), "ON"), $._expression),
        seq(
          alias(kw("using"), "USING"),
          "(",
          commaSep1($._id),
          ")",
        ),
      ),

    // A FROM-clause source: a named table (with optional alias and
    // INDEXED BY), or a parenthesised subquery (with optional alias).
    // parse.y `seltablist` lines 723-738.
    table_or_subquery: ($) =>
      choice(
        // Table-valued function: name(args) or schema.name(args).
        // parse.y `seltablist ::= LP nm DOT nm LP exprlist RP ...`.
        seq(
          $.qualified_table_name,
          "(",
          optional(commaSep1(field("argument", $._expression))),
          ")",
          optional(seq(
            optional(alias(kw("as"), "AS")),
            field("alias", $._id),
          )),
        ),
        // Plain table reference (with optional alias and INDEXED BY).
        // parse.y `seltablist ::= ... nm dbnm as indexed_opt on_using`:
        // alias precedes INDEXED BY in the rule order.
        seq(
          $.qualified_table_name,
          optional(seq(
            optional(alias(kw("as"), "AS")),
            field("alias", $._id),
          )),
          optional($._indexed_by_clause),
        ),
        // (SELECT ...) [AS? alias]
        seq(
          "(",
          alias($._select_compound, $.select_clause),
          ")",
          optional(seq(
            optional(alias(kw("as"), "AS")),
            field("alias", $._id),
          )),
        ),
        // Parenthesized join group: `(t2 JOIN t3 ON ...)` etc.
        // parse.y `seltablist ::= ... LP seltablist RP ...`.
        // Lets nested JOIN groupings appear as a FROM-clause source.
        seq(
          "(",
          $._join_clause,
          ")",
          optional(seq(
            optional(alias(kw("as"), "AS")),
            field("alias", $._id),
          )),
        ),
      ),

    group_by_clause: ($) =>
      seq(
        alias(kw("group"), "GROUP"),
        alias(kw("by"), "BY"),
        commaSep1(field("expression", $._expression)),
      ),

    // parse.y `having_opt`: HAVING is grammatically separable from
    // GROUP BY (sqlite accepts e.g. `SELECT count(*) FROM t HAVING ...`
    // without a GROUP BY clause; see count.test:129).
    having_clause: ($) =>
      seq(
        alias(kw("having"), "HAVING"),
        field("having", $._expression),
      ),

    // -------------------- DELETE (parse.y lines 919-939) --------------------
    //
    // cmd ::= with DELETE FROM xfullname indexed_opt where_opt_ret
    //         [orderby_opt limit_opt]      <- when SQLITE_ENABLE_UPDATE_DELETE_LIMIT
    //
    // Covers: DELETE FROM target [INDEXED BY name | NOT INDEXED]
    //         [WHERE expr] [ORDER BY ... LIMIT ...]
    //         [RETURNING ...] ;
    //
    // ORDER BY + LIMIT on DELETE is gated on
    // SQLITE_ENABLE_UPDATE_DELETE_LIMIT in upstream sqlite. Per the
    // README "translation notes" we admit the un-OMIT version of
    // every feature, so the optional ORDER BY + LIMIT clauses are
    // always part of the surface.
    delete_statement: ($) =>
      seq(
        optional(field("with", $.with_clause)),
        alias(kw("delete"), "DELETE"),
        alias(kw("from"), "FROM"),
        field("target", $.qualified_table_name),
        // parse.y `xfullname ::= nm DOT nm AS nm`: DELETE FROM accepts
        // an AS alias on the target table, used so a self-referential
        // EXISTS subquery can disambiguate (e.g. delete.test:412).
        optional(seq(
          optional(alias(kw("as"), "AS")),
          field("alias", $._id),
        )),
        optional($._indexed_by_clause),
        optional(field("where", $.where_clause)),
        optional(field("returning", $.returning_clause)),
        optional(field("order_by", $.order_by_clause)),
        optional(field("limit", $.limit_clause)),
      ),

    // -------------------- Table / column references --------------------

    // sqlite's `xfullname` rule supports schema.table and an optional
    // AS alias. AS aliases appear in SELECT and UPDATE-FROM contexts.
    //
    // Visible (not `_`-prefixed) so the `field("target", ...)`
    // wrappers in INSERT and UPDATE actually wrap a node — hidden
    // rules promote their fields up to the parent, which makes
    // `name:` and `schema:` appear at the statement level instead
    // of inside a `target:` subnode.
    qualified_table_name: ($) =>
      seq(
        optional(seq(field("schema", $._id), ".")),
        field("name", $._id),
      ),

    // -------------------- Expressions (parse.y lines 1119-1505) --------------------
    //
    // Full sqlite expression surface translated from parse.y. The
    // precedence table mirrors the %left/%right/%nonassoc directives
    // at parse.y lines 289-301. Postfix forms (IS NULL, BETWEEN, IN,
    // LIKE/GLOB/REGEXP/MATCH with optional ESCAPE, COLLATE) get the
    // same precedence as their parse.y rules, with explicit
    // [PRECEDENCE_TOKEN] annotations on the Lemon side translated to
    // tree-sitter prec.left/prec.right.
    //
    // Window/aggregate suffixes (WITHIN GROUP, FILTER, OVER, named
    // windows) and RAISE-in-trigger-body live with their respective
    // statement productions, not in the bare expression rule.
    _expression: ($) =>
      choice(
        $.numeric_literal,
        $.string_literal,
        $.blob_literal,
        $.null_literal,
        $.true_literal,
        $.false_literal,
        $.current_time_literal,
        $.bind_parameter,
        $.column_reference,
        // External-scanner-emitted poison tokens (src/scanner.c). These
        // appear in the tree wherever sqlite tokenize.c would have
        // emitted a malformed-token diagnostic. IDE consumers and our
        // harnesses treat these node types as parse failures.
        $.malformed_blob_literal,
        $.malformed_number_id,
        $.parenthesized_expression,
        $.tuple_expression,
        $.cast_expression,
        $.case_expression,
        $.function_call,
        $.subquery_expression,
        $.exists_expression,
        $.unary_expression,
        $.binary_expression,
        $.collate_expression,
        $.is_null_expression,
        $.is_expression,
        $.between_expression,
        $.in_list_expression,
        $.in_subquery_expression,
        $.in_table_expression,
        $.like_expression,
      ),

    null_literal: ($) => alias(kw("null"), "NULL"),
    true_literal: ($) => alias(kw("true"), "TRUE"),
    false_literal: ($) => alias(kw("false"), "FALSE"),

    // CURRENT_DATE / CURRENT_TIME / CURRENT_TIMESTAMP — TK_CTIME_KW
    // per mkkeywordhash.c. These are constants in expression context.
    current_time_literal: ($) =>
      choice(
        alias(kw("current_date"), "CURRENT_DATE"),
        alias(kw("current_time"), "CURRENT_TIME"),
        alias(kw("current_timestamp"), "CURRENT_TIMESTAMP"),
      ),

    // parse.y `expr ::= idj | nm DOT nm | nm DOT nm DOT nm` —
    // bare-identifier column reference, table-qualified, or
    // schema-qualified.
    column_reference: ($) =>
      choice(
        seq(
          field("schema", $._id),
          ".",
          field("table", $._id),
          ".",
          field("name", $._id),
        ),
        seq(field("table", $._id), ".", field("name", $._id)),
        field("name", $._id),
      ),

    parenthesized_expression: ($) =>
      seq("(", $._expression, ")"),

    // (a, b, c) — tuple expression. Used in row-form comparisons
    // (`(a,b) IN ((1,2),(3,4))`) and elsewhere.
    // parse.y line 1272: expr ::= LP nexprlist COMMA expr RP.
    tuple_expression: ($) =>
      seq(
        "(",
        $._expression,
        ",",
        commaSep1($._expression),
        ")",
      ),

    // CAST(expr AS type)
    // parse.y line 1167. The type token is intentionally permissive
    // (sqlite has dynamic typing; `CAST(x AS BANANA)` parses).
    cast_expression: ($) =>
      seq(
        alias(kw("cast"), "CAST"),
        "(",
        field("value", $._expression),
        alias(kw("as"), "AS"),
        field("type", $.type_name),
        ")",
      ),

    // sqlite type names are essentially "any sequence of identifiers,
    // optionally followed by (size) or (size, scale)".
    type_name: ($) =>
      seq(
        repeat1($._id),
        // parse.y `typetoken ::= typename LP signed RP | LP signed COMMA
        // signed RP`: the size args allow signed literals, e.g.
        // `VARCHAR(+1,-10)`. They may also be sqlite's broader signed
        // form including a leading + or -.
        optional(seq(
          "(",
          $._signed_term,
          optional(seq(",", $._signed_term)),
          ")",
        )),
      ),

    // CASE [base] WHEN cond THEN result [...] [ELSE result] END
    // parse.y line 1472.
    case_expression: ($) =>
      seq(
        alias(kw("case"), "CASE"),
        optional(field("subject", $._expression)),
        repeat1(seq(
          alias(kw("when"), "WHEN"),
          field("when", $._expression),
          alias(kw("then"), "THEN"),
          field("then", $._expression),
        )),
        optional(seq(
          alias(kw("else"), "ELSE"),
          field("else", $._expression),
        )),
        alias(kw("end"), "END"),
      ),

    // Function call — parse.y lines 1174-1181 plus the FILTER/OVER
    // variants on later lines.
    //
    //   func(*)                      — count(*) shape
    //   func(arg, ...)
    //   func(DISTINCT arg, ...)
    //   func(arg ORDER BY sort_term, ...)
    //
    // Function name uses `idj` (id|INDEXED|JOIN_KW) per parse.y —
    // we accept any identifier (the idj-keyword fallback distinction
    // is mostly relevant inside FROM/JOIN context).
    function_call: ($) =>
      seq(
        field("name", $._id),
        "(",
        optional(field("arguments", $._function_arguments)),
        ")",
        // FILTER (WHERE expr) — aggregate filter clause
        // (parse.y filter_over).
        optional(field("filter", $.filter_clause)),
        // OVER ( window-defn ) | OVER name — window function
        // wrapper (parse.y over_clause).
        optional(field("over", $.over_clause)),
      ),

    filter_clause: ($) =>
      seq(
        alias(kw("filter"), "FILTER"),
        "(",
        alias(kw("where"), "WHERE"),
        $._expression,
        ")",
      ),

    over_clause: ($) =>
      seq(
        alias(kw("over"), "OVER"),
        choice(
          field("window_name", $._id),
          seq("(", optional($.window_definition), ")"),
        ),
      ),

    // parse.y window rule (lines 1923-1939). May start with a base
    // window name to inherit from, then partition / order / frame.
    window_definition: ($) =>
      choice(
        seq(
          field("base", $._id),
          optional($.window_partition_clause),
          optional($.order_by_clause),
          optional($.window_frame_clause),
        ),
        seq(
          $.window_partition_clause,
          optional($.order_by_clause),
          optional($.window_frame_clause),
        ),
        seq(
          $.order_by_clause,
          optional($.window_frame_clause),
        ),
        $.window_frame_clause,
      ),

    window_partition_clause: ($) =>
      seq(
        alias(kw("partition"), "PARTITION"),
        alias(kw("by"), "BY"),
        commaSep1(field("expression", $._expression)),
      ),

    // parse.y `frame_opt` rule. sqlite is MORE lenient than the SQL
    // standard about which frame-bound forms can appear at start vs
    // end of a BETWEEN; it accepts e.g. `BETWEEN n FOLLOWING AND m
    // FOLLOWING` as start-FOLLOWING (window2.test, window3.test). We
    // keep the rule permissive — the few specific shapes sqlite does
    // reject (window6.test:240+, "RANGE UNBOUNDED FOLLOWING" alone)
    // would require semantic checks beyond pure syntax.
    window_frame_clause: ($) =>
      seq(
        field("kind", choice(
          alias(kw("range"), "RANGE"),
          alias(kw("rows"), "ROWS"),
          alias(kw("groups"), "GROUPS"),
        )),
        choice(
          field("bound", $.window_frame_bound),
          seq(
            alias(kw("between"), "BETWEEN"),
            field("start", $.window_frame_bound),
            alias(kw("and"), "AND"),
            field("end", $.window_frame_bound),
          ),
        ),
        optional(field("exclude", $.window_frame_exclude)),
      ),

    window_frame_bound: ($) =>
      choice(
        seq(
          alias(kw("unbounded"), "UNBOUNDED"),
          alias(kw("preceding"), "PRECEDING"),
        ),
        seq(
          alias(kw("unbounded"), "UNBOUNDED"),
          alias(kw("following"), "FOLLOWING"),
        ),
        seq(
          alias(kw("current"), "CURRENT"),
          alias(kw("row"), "ROW"),
        ),
        seq(
          $._expression,
          alias(kw("preceding"), "PRECEDING"),
        ),
        seq(
          $._expression,
          alias(kw("following"), "FOLLOWING"),
        ),
      ),

    window_frame_exclude: ($) =>
      seq(
        alias(kw("exclude"), "EXCLUDE"),
        choice(
          seq(alias(kw("no"), "NO"), alias(kw("others"), "OTHERS")),
          seq(alias(kw("current"), "CURRENT"), alias(kw("row"), "ROW")),
          alias(kw("group"), "GROUP"),
          alias(kw("ties"), "TIES"),
        ),
      ),

    _function_arguments: ($) =>
      choice(
        $.star_argument,
        $.normal_function_arguments,
      ),

    star_argument: ($) => "*",

    // sqlite 3.44+ allows aggregate functions to take ORDER BY as part
    // of their argument list, including the bare-ORDER-BY case where
    // there are no value arguments (e.g. `count(ORDER BY a)`). sqlite
    // also accepts `count(DISTINCT)` (DISTINCT alone, no args) — see
    // count.test:121. The branches below cover:
    //   - args [ORDER BY ...]              (with optional DISTINCT)
    //   - bare ORDER BY                    (with optional DISTINCT)
    //   - bare DISTINCT                    (no args, no ORDER BY)
    normal_function_arguments: ($) =>
      choice(
        seq(
          optional(field("modifier", choice(
            alias(kw("distinct"), "DISTINCT"),
            alias(kw("all"), "ALL"),
          ))),
          commaSep1($._expression),
          optional($.order_by_clause),
        ),
        seq(
          optional(field("modifier", choice(
            alias(kw("distinct"), "DISTINCT"),
            alias(kw("all"), "ALL"),
          ))),
          $.order_by_clause,
        ),
        alias(kw("distinct"), "DISTINCT"),
      ),

    // -------------------- Subquery expressions --------------------
    //
    // (SELECT ...)   — scalar subquery, used as a value
    // EXISTS(SELECT) — boolean
    // expr IN (SELECT) / expr IN (table) / expr IN (a,b,c) — three
    //   IN forms, three different rules in parse.y.
    subquery_expression: ($) =>
      seq("(", alias($._select_compound, $.select_clause), ")"),

    exists_expression: ($) =>
      seq(
        alias(kw("exists"), "EXISTS"),
        "(",
        alias($._select_compound, $.select_clause),
        ")",
      ),

    // -------------------- Unary --------------------

    unary_expression: ($) =>
      prec.right(PREC.UNARY, seq(
        field("operator", choice(
          "-",
          "+",
          "~",
          alias(kw("not"), "NOT"),
        )),
        field("operand", $._expression),
      )),

    // -------------------- Binary operators (parse.y lines 1285-1379) --------------------
    //
    // Each operator gets its precedence from the %left/%right line
    // it appears on in parse.y. The full table is at the top of this
    // file (PREC).
    binary_expression: ($) =>
      choice(
        // %left OR
        prec.left(PREC.OR, seq(
          field("left", $._expression),
          field("operator", alias(kw("or"), "OR")),
          field("right", $._expression),
        )),
        // %left AND
        prec.left(PREC.AND, seq(
          field("left", $._expression),
          field("operator", alias(kw("and"), "AND")),
          field("right", $._expression),
        )),
        // %left IS MATCH LIKE_KW BETWEEN IN ISNULL NOTNULL NE EQ
        // The IS-binary form (`x IS y`) is handled by is_expression
        // below as a separate rule because of `IS NOT`/`IS NOT
        // DISTINCT FROM` extensions.
        ...["=", "==", "!=", "<>"].map((op) =>
          prec.left(PREC.COMPARE, seq(
            field("left", $._expression),
            field("operator", op),
            field("right", $._expression),
          ))
        ),
        prec.left(PREC.COMPARE, seq(
          field("left", $._expression),
          optional(alias(kw("not"), "NOT")),
          field("operator", alias(kw("match"), "MATCH")),
          field("right", $._expression),
        )),
        // %left GT LE LT GE
        ...["<", "<=", ">", ">="].map((op) =>
          prec.left(PREC.ORDER, seq(
            field("left", $._expression),
            field("operator", op),
            field("right", $._expression),
          ))
        ),
        // %left BITAND BITOR LSHIFT RSHIFT
        ...["&", "|", "<<", ">>"].map((op) =>
          prec.left(PREC.BITWISE, seq(
            field("left", $._expression),
            field("operator", op),
            field("right", $._expression),
          ))
        ),
        // %left PLUS MINUS
        ...["+", "-"].map((op) =>
          prec.left(PREC.ADD, seq(
            field("left", $._expression),
            field("operator", op),
            field("right", $._expression),
          ))
        ),
        // %left STAR SLASH REM
        ...["*", "/", "%"].map((op) =>
          prec.left(PREC.MUL, seq(
            field("left", $._expression),
            field("operator", op),
            field("right", $._expression),
          ))
        ),
        // %left CONCAT PTR
        // PTR is sqlite's `->` and `->>` (JSON path access),
        // line 1379 of parse.y.
        ...["||", "->", "->>"].map((op) =>
          prec.left(PREC.CONCAT, seq(
            field("left", $._expression),
            field("operator", op),
            field("right", $._expression),
          ))
        ),
      ),

    // expr COLLATE name — postfix, %left COLLATE.
    // parse.y line 1163.
    collate_expression: ($) =>
      prec.left(PREC.COLLATE, seq(
        field("operand", $._expression),
        alias(kw("collate"), "COLLATE"),
        field("collation", $._id),
      )),

    // expr IS NULL / NOTNULL — postfix at COMPARE precedence.
    // parse.y lines 1322-1323.
    is_null_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("operand", $._expression),
        field("operator", choice(
          alias(kw("isnull"), "ISNULL"),
          alias(kw("notnull"), "NOTNULL"),
          seq(alias(kw("not"), "NOT"), alias(kw("null"), "NULL")),
        )),
      )),

    // expr IS [NOT] [DISTINCT FROM] expr — parse.y lines 1344-1356.
    // All four forms at COMPARE precedence.
    is_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("left", $._expression),
        alias(kw("is"), "IS"),
        optional(alias(kw("not"), "NOT")),
        optional(seq(
          alias(kw("distinct"), "DISTINCT"),
          alias(kw("from"), "FROM"),
        )),
        field("right", $._expression),
      )),

    // expr [NOT] BETWEEN expr AND expr — parse.y line 1388.
    // Precedence label [BETWEEN] in parse.y resolves to the COMPARE
    // class line.
    between_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("operand", $._expression),
        optional(alias(kw("not"), "NOT")),
        alias(kw("between"), "BETWEEN"),
        field("low", $._expression),
        alias(kw("and"), "AND"),
        field("high", $._expression),
      )),

    // expr [NOT] IN (expr-list) — parse.y line 1403.
    in_list_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("operand", $._expression),
        optional(alias(kw("not"), "NOT")),
        alias(kw("in"), "IN"),
        "(",
        optional(field("values", commaSep1($._expression))),
        ")",
      )),

    // expr [NOT] IN (SELECT ...) — parse.y line 1451.
    in_subquery_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("operand", $._expression),
        optional(alias(kw("not"), "NOT")),
        alias(kw("in"), "IN"),
        "(",
        alias($._select_compound, $.select_clause),
        ")",
      )),

    // expr [NOT] IN [schema.]table [(args)] — parse.y line 1456.
    // Used for table-name-as-rowset in IN.
    in_table_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("operand", $._expression),
        optional(alias(kw("not"), "NOT")),
        alias(kw("in"), "IN"),
        $.qualified_table_name,
        optional(seq("(", commaSep1($._expression), ")")),
      )),

    // expr [NOT] LIKE/GLOB/REGEXP/MATCH expr [ESCAPE expr]
    // parse.y lines 1300-1310. LIKE_KW class includes LIKE/GLOB/
    // REGEXP per mkkeywordhash.c (all → TK_LIKE_KW).
    like_expression: ($) =>
      prec.left(PREC.COMPARE, seq(
        field("operand", $._expression),
        optional(alias(kw("not"), "NOT")),
        field("operator", choice(
          alias(kw("like"), "LIKE"),
          alias(kw("glob"), "GLOB"),
          alias(kw("regexp"), "REGEXP"),
        )),
        field("pattern", $._expression),
        optional(seq(
          alias(kw("escape"), "ESCAPE"),
          field("escape", $._expression),
        )),
      )),

    // -------------------- DDL: CREATE TABLE (parse.y lines 188-462) --------------------
    //
    // create_table ::= createkw temp TABLE ifnotexists nm dbnm
    // create_table_args ::= LP columnlist conslist_opt RP table_option_set
    //                     | AS select
    //
    // columnlist ::= columnname carglist [, columnname carglist]*
    // columnname ::= nm typetoken
    // carglist   ::= ccons*
    // ccons      ::= [CONSTRAINT name] one-of:
    //                  NULL onconf
    //                  NOT NULL onconf
    //                  PRIMARY KEY sortorder onconf [AUTOINCREMENT]
    //                  UNIQUE onconf
    //                  CHECK (expr) onconf
    //                  DEFAULT term | DEFAULT (expr) | ...
    //                  COLLATE name
    //                  REFERENCES name [(cols)] refargs
    //                  GENERATED ALWAYS AS (expr) [STORED|VIRTUAL]
    //                  AS (expr) [STORED|VIRTUAL]
    //                  defer_subclause
    create_table_statement: ($) =>
      seq(
        alias(kw("create"), "CREATE"),
        optional(field("temporary", choice(
          alias(kw("temp"), "TEMP"),
          alias(kw("temporary"), "TEMPORARY"),
        ))),
        alias(kw("table"), "TABLE"),
        optional($._if_not_exists),
        field("name", $.qualified_table_name),
        choice(
          $._create_table_columns,
          seq(
            alias(kw("as"), "AS"),
            alias($._select_compound, $.select_clause),
          ),
        ),
      ),

    _create_table_columns: ($) =>
      seq(
        "(",
        // parse.y `columnlist` is a comma-separated list of column
        // defs OR table constraints. Additionally `conslist ::=
        // conslist tcons` chains multiple constraints WITHOUT comma —
        // sqlite accepts e.g. `PRIMARY KEY(a) UNIQUE (a) CONSTRAINT
        // one` as three table_constraints back-to-back. Model that
        // as: each comma-item is a column or one-or-more constraints.
        commaSep1(choice(
          field("column", $.column_definition),
          repeat1(field("constraint", $.table_constraint)),
        )),
        ")",
        optional(field("options", $.table_options)),
      ),

    column_definition: ($) =>
      seq(
        field("name", $._id),
        optional(field("type", $.type_name)),
        repeat(field("constraint", $.column_constraint)),
      ),

    column_constraint: ($) =>
      choice(
        // parse.y `ccons ::= CONSTRAINT nm` — bare CONSTRAINT name with
        // no body parses as a no-op column-level constraint. This
        // also supports the stacked-CONSTRAINT-NAMES pattern
        // `CONSTRAINT one CONSTRAINT two CHECK(...)`: each pair of
        // (name + body) is one column_constraint, and the first names
        // without bodies become bare-name column_constraints.
        seq(
          alias(kw("constraint"), "CONSTRAINT"),
          field("name", $._id),
        ),
        seq(
        optional(seq(
          alias(kw("constraint"), "CONSTRAINT"),
          field("name", $._id),
        )),
        choice(
          // NOT NULL onconf
          seq(
            alias(kw("not"), "NOT"),
            alias(kw("null"), "NULL"),
            optional($._on_conflict_clause),
          ),
          // NULL onconf — sqlite allows but it's a no-op
          seq(
            alias(kw("null"), "NULL"),
            optional($._on_conflict_clause),
          ),
          // PRIMARY KEY [ASC|DESC] onconf [AUTOINCREMENT]
          seq(
            alias(kw("primary"), "PRIMARY"),
            alias(kw("key"), "KEY"),
            optional(choice(
              alias(kw("asc"), "ASC"),
              alias(kw("desc"), "DESC"),
            )),
            optional($._on_conflict_clause),
            optional(alias(kw("autoincrement"), "AUTOINCREMENT")),
          ),
          // UNIQUE onconf
          seq(
            alias(kw("unique"), "UNIQUE"),
            optional($._on_conflict_clause),
          ),
          // CHECK (expr)
          // parse.y `ccons ::= CHECK LP expr RP` (NO onconf at the
          // column level — sqlite explicitly rejects ON CONFLICT on
          // column CHECK constraints; see check.test:1136 comment).
          seq(
            alias(kw("check"), "CHECK"),
            "(",
            field("check", $._expression),
            ")",
          ),
          // DEFAULT (expr) | DEFAULT [+/-] term
          // _signed_term covers the `[+/-] (numeric | NULL | TRUE |
          // FALSE | string | blob)` forms — sqlite accepts a sign
          // prefix on string and blob too (tkt-8454a207b9).
          seq(
            alias(kw("default"), "DEFAULT"),
            field("default", choice(
              seq("(", $._expression, ")"),
              $._signed_term,
              $._id,
            )),
          ),
          // COLLATE name
          seq(
            alias(kw("collate"), "COLLATE"),
            field("collation", $._id),
          ),
          // REFERENCES table [(cols)] refargs (foreign-key column-level)
          $.foreign_key_clause,
          // GENERATED ALWAYS AS (expr) [STORED|VIRTUAL]
          seq(
            optional(seq(
              alias(kw("generated"), "GENERATED"),
              alias(kw("always"), "ALWAYS"),
            )),
            alias(kw("as"), "AS"),
            "(",
            field("generated_expression", $._expression),
            ")",
            optional(field("storage", choice(
              alias(kw("stored"), "STORED"),
              alias(kw("virtual"), "VIRTUAL"),
            ))),
          ),
          // [NOT] DEFERRABLE [INITIALLY DEFERRED|IMMEDIATE]
          seq(
            optional(alias(kw("not"), "NOT")),
            alias(kw("deferrable"), "DEFERRABLE"),
            optional(seq(
              alias(kw("initially"), "INITIALLY"),
              choice(
                alias(kw("deferred"), "DEFERRED"),
                alias(kw("immediate"), "IMMEDIATE"),
              ),
            )),
          ),
        ),
        ),
      ),

    _signed_term: ($) =>
      seq(
        optional(choice("+", "-")),
        choice(
          $.numeric_literal,
          $.null_literal,
          $.true_literal,
          $.false_literal,
          $.string_literal,
          $.blob_literal,
        ),
      ),

    _on_conflict_clause: ($) =>
      seq(
        alias(kw("on"), "ON"),
        alias(kw("conflict"), "CONFLICT"),
        $._resolve_type,
      ),

    // parse.y splits `REFERENCES ...` and `defer_subclause` into two
    // separate `ccons` (column constraint) branches. We follow that
    // split: foreign_key_clause covers REFERENCES + ON-actions +
    // MATCH; the [NOT] DEFERRABLE clause is its own column_constraint
    // branch. Combining them led to a tree-sitter conflict where NOT
    // could begin either a deferrable continuation or a new
    // NOT-NULL column_constraint.
    foreign_key_clause: ($) =>
      seq(
        alias(kw("references"), "REFERENCES"),
        field("table", $._id),
        optional(seq(
          "(",
          commaSep1(field("column", $._id)),
          ")",
        )),
        repeat(field("action", $._fk_action)),
      ),

    _fk_action: ($) =>
      choice(
        seq(
          alias(kw("on"), "ON"),
          choice(
            alias(kw("delete"), "DELETE"),
            alias(kw("update"), "UPDATE"),
          ),
          choice(
            alias(kw("cascade"), "CASCADE"),
            alias(kw("restrict"), "RESTRICT"),
            seq(alias(kw("set"), "SET"), alias(kw("null"), "NULL")),
            seq(alias(kw("set"), "SET"), alias(kw("default"), "DEFAULT")),
            seq(alias(kw("no"), "NO"), alias(kw("action"), "ACTION")),
          ),
        ),
        seq(
          alias(kw("match"), "MATCH"),
          field("match_type", $._id),
        ),
      ),

    table_constraint: ($) =>
      choice(
        // parse.y `tcons ::= CONSTRAINT nm` — bare CONSTRAINT name
        // with no body parses as a no-op table-level constraint
        // (schema5.test:25 — `PRIMARY KEY(a) UNIQUE(a) CONSTRAINT one`
        // ends with a body-less CONSTRAINT).
        seq(
          alias(kw("constraint"), "CONSTRAINT"),
          field("name", $._id),
        ),
        seq(
          optional(seq(
            alias(kw("constraint"), "CONSTRAINT"),
            field("name", $._id),
          )),
          choice(
          // PRIMARY KEY (sortlist [AUTOINCREMENT]) onconf
          // parse.y `tcons ::= PRIMARY KEY LP sortlist autoinc RP
          // onconf` — AUTOINCREMENT appears AFTER the sort-list,
          // INSIDE the parens (autoinc.test:504).
          seq(
            alias(kw("primary"), "PRIMARY"),
            alias(kw("key"), "KEY"),
            "(",
            commaSep1(field("column", $.indexed_column)),
            optional(alias(kw("autoincrement"), "AUTOINCREMENT")),
            ")",
            optional($._on_conflict_clause),
          ),
          // UNIQUE (col-list) onconf
          seq(
            alias(kw("unique"), "UNIQUE"),
            "(",
            commaSep1(field("column", $.indexed_column)),
            ")",
            optional($._on_conflict_clause),
          ),
          // CHECK (expr) [ON CONFLICT ...]
          // parse.y `ccons ::= CHECK LP expr RP onconf` and `tcons ::=
          // CHECK LP expr RP onconf` — both column-level and
          // table-level CHECK accept an ON CONFLICT clause.
          seq(
            alias(kw("check"), "CHECK"),
            "(",
            field("check", $._expression),
            ")",
            optional($._on_conflict_clause),
          ),
          // FOREIGN KEY (cols) REFERENCES ... [[NOT] DEFERRABLE ...]
          // parse.y `tcons ::= FOREIGN KEY LP eidlist RP REFERENCES nm
          //                    eidlist_opt refargs defer_subclause_opt`.
          seq(
            alias(kw("foreign"), "FOREIGN"),
            alias(kw("key"), "KEY"),
            "(",
            commaSep1(field("column", $._id)),
            ")",
            $.foreign_key_clause,
            optional(seq(
              optional(alias(kw("not"), "NOT")),
              alias(kw("deferrable"), "DEFERRABLE"),
              optional(seq(
                alias(kw("initially"), "INITIALLY"),
                choice(
                  alias(kw("deferred"), "DEFERRED"),
                  alias(kw("immediate"), "IMMEDIATE"),
                ),
              )),
            )),
          ),
          ),
        ),
      ),

    // sqlite's "indexed column" — used in CREATE INDEX, PRIMARY KEY,
    // UNIQUE constraints. Allows expressions, COLLATE, sort order.
    indexed_column: ($) =>
      seq(
        field("expression", $._expression),
        optional(seq(
          alias(kw("collate"), "COLLATE"),
          field("collation", $._id),
        )),
        optional(field("order", choice(
          alias(kw("asc"), "ASC"),
          alias(kw("desc"), "DESC"),
        ))),
        // parse.y `sortlist`-style NULLS FIRST/LAST is also accepted
        // in PRIMARY KEY / UNIQUE indexed-column lists, see
        // nulls1.test:254.
        optional(seq(
          alias(kw("nulls"), "NULLS"),
          choice(
            alias(kw("first"), "FIRST"),
            alias(kw("last"), "LAST"),
          ),
        )),
      ),

    table_options: ($) =>
      commaSep1(choice(
        // parse.y `tabopt`: WITHOUT followed by an identifier. Only
        // ROWID is meaningful but the parser accepts any identifier
        // (without_rowid5.test exercises `WITHOUT _rowid_`, `WITHOUT
        // oid`, `WITHOUT unknown2` etc., which all parse).
        seq(
          alias(kw("without"), "WITHOUT"),
          field("option", $._id),
        ),
        alias(kw("strict"), "STRICT"),
      )),

    _if_not_exists: ($) =>
      seq(
        alias(kw("if"), "IF"),
        alias(kw("not"), "NOT"),
        alias(kw("exists"), "EXISTS"),
      ),

    _if_exists: ($) =>
      seq(
        alias(kw("if"), "IF"),
        alias(kw("exists"), "EXISTS"),
      ),

    // -------------------- DDL: ALTER TABLE --------------------
    //
    // parse.y line ~1670:
    //   ALTER TABLE fullname RENAME TO nm
    //   ALTER TABLE fullname RENAME [COLUMN] nm TO nm
    //   ALTER TABLE fullname ADD [COLUMN] columnname carglist
    //   ALTER TABLE fullname DROP [COLUMN] nm
    alter_table_statement: ($) =>
      seq(
        alias(kw("alter"), "ALTER"),
        alias(kw("table"), "TABLE"),
        field("name", $.qualified_table_name),
        choice(
          // RENAME TO new_name
          seq(
            alias(kw("rename"), "RENAME"),
            alias(kw("to"), "TO"),
            field("new_name", $._id),
          ),
          // RENAME [COLUMN] old TO new
          seq(
            alias(kw("rename"), "RENAME"),
            optional(alias(kw("column"), "COLUMN")),
            field("old_column", $._id),
            alias(kw("to"), "TO"),
            field("new_column", $._id),
          ),
          // ADD [COLUMN] column-def
          seq(
            alias(kw("add"), "ADD"),
            optional(alias(kw("column"), "COLUMN")),
            field("column", $.column_definition),
          ),
          // DROP [COLUMN] name
          seq(
            alias(kw("drop"), "DROP"),
            optional(alias(kw("column"), "COLUMN")),
            field("dropped_column", $._id),
          ),
        ),
      ),

    // -------------------- DDL: DROP TABLE --------------------
    //
    // parse.y line 479: DROP TABLE [IF EXISTS] fullname
    drop_table_statement: ($) =>
      seq(
        alias(kw("drop"), "DROP"),
        alias(kw("table"), "TABLE"),
        optional($._if_exists),
        field("name", $.qualified_table_name),
      ),

    // -------------------- DDL: CREATE/DROP INDEX --------------------
    //
    // parse.y line 1525:
    //   CREATE [UNIQUE] INDEX [IF NOT EXISTS] [schema.]name
    //          ON name (indexed-col [, ...]) [WHERE expr]
    create_index_statement: ($) =>
      seq(
        alias(kw("create"), "CREATE"),
        optional(field("unique", alias(kw("unique"), "UNIQUE"))),
        alias(kw("index"), "INDEX"),
        optional($._if_not_exists),
        field("name", $.qualified_table_name),
        alias(kw("on"), "ON"),
        field("table", $._id),
        "(",
        commaSep1(field("column", $.indexed_column)),
        ")",
        optional(field("where", $.where_clause)),
      ),

    drop_index_statement: ($) =>
      seq(
        alias(kw("drop"), "DROP"),
        alias(kw("index"), "INDEX"),
        optional($._if_exists),
        field("name", $.qualified_table_name),
      ),

    // -------------------- DDL: CREATE/DROP VIEW --------------------
    //
    // parse.y line 489:
    //   CREATE [TEMP] VIEW [IF NOT EXISTS] [schema.]name [(col-list)]
    //          AS select
    create_view_statement: ($) =>
      seq(
        alias(kw("create"), "CREATE"),
        optional(field("temporary", choice(
          alias(kw("temp"), "TEMP"),
          alias(kw("temporary"), "TEMPORARY"),
        ))),
        alias(kw("view"), "VIEW"),
        optional($._if_not_exists),
        field("name", $.qualified_table_name),
        optional(seq(
          "(",
          commaSep1(field("column", $._id)),
          ")",
        )),
        alias(kw("as"), "AS"),
        field("body", alias($._select_compound, $.select_clause)),
      ),

    drop_view_statement: ($) =>
      seq(
        alias(kw("drop"), "DROP"),
        alias(kw("view"), "VIEW"),
        optional($._if_exists),
        field("name", $.qualified_table_name),
      ),

    // -------------------- DDL: CREATE/DROP TRIGGER --------------------
    //
    // parse.y line 1639:
    //   CREATE [TEMP] TRIGGER [IF NOT EXISTS] [schema.]name
    //          [BEFORE|AFTER|INSTEAD OF] event ON table
    //          [FOR EACH ROW] [WHEN expr]
    //          BEGIN trigger_cmd_list END
    //
    // event: DELETE | INSERT | UPDATE [OF col-list]
    //
    // trigger_cmd_list: trigger_cmd ; [trigger_cmd ;]*
    // trigger_cmd: UPDATE | INSERT | DELETE | SELECT
    //              (subset of full statement productions; sqlite
    //              forbids CTE/RETURNING in trigger bodies, but the
    //              syntax allows them — we admit the full forms and
    //              defer that constraint to the consumer)
    create_trigger_statement: ($) =>
      seq(
        alias(kw("create"), "CREATE"),
        optional(field("temporary", choice(
          alias(kw("temp"), "TEMP"),
          alias(kw("temporary"), "TEMPORARY"),
        ))),
        alias(kw("trigger"), "TRIGGER"),
        optional($._if_not_exists),
        field("name", $.qualified_table_name),
        optional(field("timing", choice(
          alias(kw("before"), "BEFORE"),
          alias(kw("after"), "AFTER"),
          seq(alias(kw("instead"), "INSTEAD"), alias(kw("of"), "OF")),
        ))),
        field("event", $.trigger_event),
        alias(kw("on"), "ON"),
        field("table", $.qualified_table_name),
        optional(seq(
          alias(kw("for"), "FOR"),
          alias(kw("each"), "EACH"),
          alias(kw("row"), "ROW"),
        )),
        optional(seq(
          alias(kw("when"), "WHEN"),
          field("when", $._expression),
        )),
        alias(kw("begin"), "BEGIN"),
        // parse.y `trigger_cmd_list ::= trigger_cmd_list trigger_cmd SEMI`:
        // each statement inside the trigger body is `;`-terminated.
        repeat1(seq(field("body", $._trigger_body_statement), ";")),
        alias(kw("end"), "END"),
      ),

    trigger_event: ($) =>
      choice(
        alias(kw("delete"), "DELETE"),
        alias(kw("insert"), "INSERT"),
        seq(
          alias(kw("update"), "UPDATE"),
          optional(seq(
            alias(kw("of"), "OF"),
            commaSep1(field("column", $._id)),
          )),
        ),
      ),

    _trigger_body_statement: ($) =>
      choice(
        $.select_statement,
        $.insert_statement,
        $.update_statement,
        $.delete_statement,
      ),

    drop_trigger_statement: ($) =>
      seq(
        alias(kw("drop"), "DROP"),
        alias(kw("trigger"), "TRIGGER"),
        optional($._if_exists),
        field("name", $.qualified_table_name),
      ),

    // -------------------- DDL: CREATE VIRTUAL TABLE --------------------
    //
    // parse.y: cmd ::= createkw VIRTUAL TABLE ifnotexists nm dbnm
    //                  USING nm vtabarglist
    //
    // The module-arglist is intentionally permissive — virtual
    // table modules accept arbitrary arg syntax.
    create_virtual_table_statement: ($) =>
      seq(
        alias(kw("create"), "CREATE"),
        alias(kw("virtual"), "VIRTUAL"),
        alias(kw("table"), "TABLE"),
        optional($._if_not_exists),
        field("name", $.qualified_table_name),
        alias(kw("using"), "USING"),
        field("module", $._id),
        optional(seq(
          "(",
          optional(field("module_arguments",
            commaSep1($._vtab_arg))),
          ")",
        )),
      ),

    // Module args are arbitrary token sequences separated by top-level
    // commas. parse.y's vtabargtoken is `ANY`. Each arg is wrapped in
    // a named `vtab_module_arg` so its text is preserved in the tree
    // (inline anonymous tokens get inlined out of the leaf walk, which
    // breaks the roundtrip property).
    _vtab_arg: ($) => $.vtab_module_arg,

    vtab_module_arg: ($) =>
      repeat1(choice(
        token(/(?:'(?:[^']|'')*'|"(?:[^"]|"")*"|[^,()'"])+/),
        seq("(", repeat($._vtab_arg_inner), ")"),
        $.malformed_blob_literal,
        $.malformed_number_id,
      )),

    _vtab_arg_inner: ($) =>
      choice(
        token(/(?:'(?:[^']|'')*'|"(?:[^"]|"")*"|[^()'"])+/),
        seq("(", repeat($._vtab_arg_inner), ")"),
      ),

    // -------------------- sqlite-specific statements --------------------
    //
    // ATTACH/DETACH, PRAGMA, VACUUM, REINDEX, ANALYZE, EXPLAIN,
    // transaction control (BEGIN/COMMIT/ROLLBACK/SAVEPOINT/RELEASE),
    // and dot-commands (which are not in parse.y — they live in
    // shell.c, vendored at vendor/shell.c).

    // ATTACH [DATABASE] expr AS expr [KEY expr]   (parse.y line 1765)
    attach_statement: ($) =>
      seq(
        alias(kw("attach"), "ATTACH"),
        optional(alias(kw("database"), "DATABASE")),
        field("source", $._expression),
        alias(kw("as"), "AS"),
        field("schema", $._expression),
        optional(seq(
          alias(kw("key"), "KEY"),
          field("key", $._expression),
        )),
      ),

    // DETACH [DATABASE] expr                      (parse.y line 1768)
    detach_statement: ($) =>
      seq(
        alias(kw("detach"), "DETACH"),
        optional(alias(kw("database"), "DATABASE")),
        field("schema", $._expression),
      ),

    // PRAGMA [schema.]name [= value | (value)]    (parse.y lines 1617-1622)
    pragma_statement: ($) =>
      seq(
        alias(kw("pragma"), "PRAGMA"),
        optional(seq(field("schema", $._id), ".")),
        field("name", $._id),
        // sqlite accepts both `=` and `==` for the PRAGMA assignment
        // operator (mirrors EQ token-class which covers both forms
        // throughout sqlite expressions).
        optional(choice(
          seq(choice("=", "=="), field("value", $._pragma_value)),
          seq("(", field("value", $._pragma_value), ")"),
        )),
      ),

    // parse.y `nmnum`:
    //   nmnum ::= plus_num | nm | ON | DELETE | DEFAULT
    // NULL is NOT in the production — `PRAGMA compile_options(NULL)`
    // is a syntax error per sqlite. parse.y explicitly enumerates ON
    // / DELETE / DEFAULT as PRAGMA values even though they are
    // reserved elsewhere.
    _pragma_value: ($) =>
      choice(
        $.numeric_literal,
        $.string_literal,
        $.true_literal,
        $.false_literal,
        $._id,
        seq(choice("+", "-"), $.numeric_literal),
        alias(kw("on"), $.identifier),
        alias(kw("delete"), $.identifier),
        alias(kw("default"), $.identifier),
      ),

    // VACUUM [schema-name] [INTO file-name]
    vacuum_statement: ($) =>
      seq(
        alias(kw("vacuum"), "VACUUM"),
        optional(field("schema", $._id)),
        // parse.y `cmd ::= VACUUM nm? INTO expr`: the destination is
        // a full expression — usually a string literal, but sqlite
        // accepts any expression form (vacuum-into.test:83 uses a
        // scalar subquery; :88-97 use names / NULL / qualified names).
        optional(seq(
          alias(kw("into"), "INTO"),
          field("destination", $._expression),
        )),
      ),

    // REINDEX [collation-name | [schema-name.]table-name]
    reindex_statement: ($) =>
      seq(
        alias(kw("reindex"), "REINDEX"),
        optional(field("target", $.qualified_table_name)),
      ),

    // ANALYZE [schema-name | [schema-name.]index-or-table]
    analyze_statement: ($) =>
      seq(
        alias(kw("analyze"), "ANALYZE"),
        optional(field("target", $.qualified_table_name)),
      ),

    // EXPLAIN [QUERY PLAN] stmt
    explain_statement: ($) =>
      seq(
        alias(kw("explain"), "EXPLAIN"),
        optional(seq(
          alias(kw("query"), "QUERY"),
          alias(kw("plan"), "PLAN"),
        )),
        field("statement", $._statement),
      ),

    // BEGIN [DEFERRED|IMMEDIATE|EXCLUSIVE] [TRANSACTION [name]]
    // parse.y `trans_opt ::= TRANSACTION nm`: TRANSACTION may carry a
    // name that sqlite parses but does not actually use (avtrans /
    // trans tests).
    begin_statement: ($) =>
      seq(
        alias(kw("begin"), "BEGIN"),
        optional(field("mode", choice(
          alias(kw("deferred"), "DEFERRED"),
          alias(kw("immediate"), "IMMEDIATE"),
          alias(kw("exclusive"), "EXCLUSIVE"),
        ))),
        optional(seq(
          alias(kw("transaction"), "TRANSACTION"),
          optional(field("name", $._id)),
        )),
      ),

    // COMMIT [TRANSACTION [name]] | END [TRANSACTION [name]]
    commit_statement: ($) =>
      seq(
        choice(
          alias(kw("commit"), "COMMIT"),
          alias(kw("end"), "END"),
        ),
        optional(seq(
          alias(kw("transaction"), "TRANSACTION"),
          optional(field("name", $._id)),
        )),
      ),

    // ROLLBACK [TRANSACTION [name]] [TO [SAVEPOINT] savepoint-name]
    rollback_statement: ($) =>
      seq(
        alias(kw("rollback"), "ROLLBACK"),
        optional(seq(
          alias(kw("transaction"), "TRANSACTION"),
          optional(field("name", $._id)),
        )),
        optional(seq(
          alias(kw("to"), "TO"),
          optional(alias(kw("savepoint"), "SAVEPOINT")),
          field("savepoint", $._id),
        )),
      ),

    // SAVEPOINT name
    savepoint_statement: ($) =>
      seq(
        alias(kw("savepoint"), "SAVEPOINT"),
        field("name", $._id),
      ),

    // RELEASE [SAVEPOINT] name
    release_statement: ($) =>
      seq(
        alias(kw("release"), "RELEASE"),
        optional(alias(kw("savepoint"), "SAVEPOINT")),
        field("name", $._id),
      ),

    // -------------------- Lexer foundation (subitem 1c) --------------------

    // sqlite tokenize.c IdChar(): identifier bytes are
    // [A-Za-z_$0-9] OR any byte >= 0x80 (which is how all non-ASCII
    // UTF-8 bytes are accepted as identifier characters). Mirror that
    // here so non-ASCII column / table names parse (join6.test, etc.).
    identifier: ($) => /[A-Za-z_-￿][A-Za-z0-9_$-￿]*/,

    // sqlite accepts a quoted identifier in three forms (per tokenize.c
    // sqlite3GetToken): "..." (ANSI delimited), `...` (MySQL-compat),
    // [...] (T-SQL-compat).
    quoted_identifier: ($) =>
      choice(
        token(seq('"', /(?:[^"]|"")*/, '"')),
        token(seq("`", /(?:[^`]|``)*/, "`")),
        token(seq("[", /[^\]]*/, "]")),
      ),

    // Hidden alias used wherever a SQL name is permitted. parse.y's
    // `nm` rule is `id|JOIN_KW|STRING` — STRING (single-quoted literal)
    // is accepted in identifier position as a sqlite-specific
    // backwards-compat fallback. We model that by including
    // string_literal here. The resulting tree node shows the
    // underlying form: (identifier), (quoted_identifier), or
    // (string_literal).
    // parse.y `nm` rule + %fallback: TRUE / FALSE / CURRENT_* and many
    // other keywords fall back to identifier in name position. We
    // model the most common cases here; more can be added as the
    // upstream corpus surfaces them. Negative precedence on these
    // branches ensures expression / clause contexts still prefer the
    // keyword interpretation.
    _id: ($) => choice(
      $.identifier,
      $.quoted_identifier,
      prec(-1, alias(kw("true"), $.identifier)),
      prec(-1, alias(kw("false"), $.identifier)),
      // WINDOW and OVER are used as table/column/alias names in
      // window6.test corpus — `SELECT sum(over) OVER over WINDOW
      // over AS (...)` etc.
      prec(-1, alias(kw("window"), $.identifier)),
      prec(-1, alias(kw("over"), $.identifier)),
      // RECURSIVE is in parse.y's %fallback list — `WITH recursive
      // AS (SELECT 1) SELECT * FROM recursive` is valid (sqlite
      // distinguishes CTE-name `recursive` from the WITH RECURSIVE
      // flag via lookahead).
      prec(-1, alias(kw("recursive"), $.identifier)),
      // String-as-identifier fallback for positions like
      // `CREATE TABLE 'foo'(...)` where only an identifier is
      // grammatically valid; expression contexts prefer string_literal.
      prec(-1, $.string_literal),
    ),

    // sqlite tokenize.c: numeric literals allow `_` only between
    // digits (single underscore as a thousands separator). Forms like
    // `123__456` (consecutive underscores) or `0xFFEF_` (trailing
    // underscore) are rejected by sqlite. Pattern `[d](_?[d])*` —
    // optional underscore followed by digit, repeated.
    numeric_literal: ($) =>
      choice(
        token(seq(
          choice("0x", "0X"),
          /[0-9a-fA-F](?:_?[0-9a-fA-F])*/,
        )),
        token(seq(
          choice(
            seq(
              /[0-9](?:_?[0-9])*/,
              optional(seq(".", optional(/[0-9](?:_?[0-9])*/))),
            ),
            seq(".", /[0-9](?:_?[0-9])*/),
          ),
          optional(seq(
            choice("e", "E"),
            optional(choice("+", "-")),
            /[0-9](?:_?[0-9])*/,
          )),
        )),
      ),

    string_literal: ($) =>
      token(seq("'", /(?:[^']|'')*/, "'")),

    // sqlite tokenize.c: blob literal is `X'<hex-pairs>'` — an even
    // number of hex digits, no embedded whitespace or non-hex chars.
    // Matching the tokenizer here means VALID forms parse as
    // blob_literal, but malformed forms (`X'01001'` odd, `X'01020
    // 100'` space, `X'01020k304'` non-hex; see blob.test:55-76) fall
    // back to (X-as-identifier, '...'-as-string), which sqlite
    // rejects at tokenize-time. Closing this gap requires an external
    // scanner — a future enhancement.
    blob_literal: ($) =>
      token(prec(1, seq(
        choice("x'", "X'"),
        /(?:[0-9a-fA-F][0-9a-fA-F])*/,
        "'",
      ))),

    bind_parameter: ($) =>
      token(choice(
        seq("?", optional(/[0-9]+/)),
        seq(
          choice(":", "@", "$", "#"),
          // Name only — sqlite rejects bare-digit forms after :,@,$,#.
          // `#1` etc. produce "near \"#1\": syntax error" (verified
          // against libsqlite3 3.47.0).
          /[A-Za-z_][A-Za-z0-9_$]*/,
        ),
      )),

    line_comment: ($) => token(seq("--", /[^\n]*/)),

    // sqlite's tokenize.c treats `/*` as a comment that runs until
    // either `*/` OR end-of-input. Bare `/*` at EOF (no chars after
    // the opener) IS rejected by sqlite (tokenize.test:58); the
    // unterminated form requires at least one char inside (which can
    // be `*` itself, e.g. `/***abc` — tokenize.test:54).
    block_comment: ($) =>
      token(choice(
        seq("/*", /[^*]*\*+([^/*][^*]*\*+)*/, "/"),
        // Unterminated, to EOF — must have at least one inner char.
        seq("/*", /./, /[^*]*(\*+[^/*][^*]*)*\**/),
      )),

    // -------------------- sqlite3 CLI dot-commands (vendor/shell.c) --------------------
    //
    // Sourced from `do_meta_command()` in vendor/shell.c. The canonical
    // list of dot-commands lives there as a chain of `cli_strncmp`
    // and `cli_strcmp` dispatches keyed off azArg[0]. We list the
    // recognized names below; an unknown `.word` still parses (via
    // the `unknown` arm) so the grammar is forgiving toward sqlite
    // CLI extensions and future dot-commands not yet in the list.
    //
    // Dot-command syntax (per shell.c parser, lines 8290-8400):
    //   line starts with `.` (no leading whitespace before the dot)
    //   followed by command name (letters / underscore / hyphen)
    //   followed by zero or more space-separated arguments
    //   terminated by newline (NOT semicolon — dot-commands aren't SQL)
    dot_command: ($) =>
      seq(
        field("name", $._dot_command_name),
        optional(field("arguments", $.dot_command_arguments)),
      ),

    // Named so the args span shows in the parse tree. Use
    // token.immediate so tree-sitter's extras handler can't strip
    // the leading whitespace BEFORE the token matches — otherwise
    // a `\n` ending a dot-command would be eaten as extras and the
    // args regex would consume the next line. The pattern requires
    // a leading space + at least one non-newline char + optional
    // trailing newline, all in one atomic token match.
    dot_command_arguments: ($) =>
      token.immediate(seq(/[ \t]+/, /[^\n]+/)),

    _dot_command_name: ($) =>
      choice(
        // Canonical names from shell.c v3.47.0 do_meta_command(), in
        // alphabetical order. Each is a separate alternative so the
        // tree records *which* command was used.
        ...[
          "archive", "auth", "backup", "bail", "binary", "boolean",
          "breakpoint", "cd", "changes", "check", "clone", "connection",
          "crlf", "crnl", "databases", "dbconfig", "dbinfo", "dump",
          "echo", "eqp", "excel", "exit", "expert", "explain",
          "filectrl", "fullschema", "headers", "help", "import",
          "imposter", "indexes", "indices", "intck", "integer",
          "iotrace", "limits", "lint", "load", "log", "mode", "nonce",
          "nullvalue", "once", "open", "output", "parameter", "print",
          "progress", "prompt", "quit", "read", "recover", "restore",
          "save", "scanstats", "schema", "selecttrace", "selftest",
          "separator", "session", "shell", "show", "stats", "system",
          "tables", "testcase", "testctrl", "timeout", "timer",
          "trace", "treetrace", "unmodule", "user", "version",
          "vfsinfo", "vfslist", "vfsname", "wheretrace", "width",
          "www",
        ].map((name) => alias(token(seq(".", name)), `.${name}`)),
        // Catch-all for unknown / future dot-commands. Tree-sitter
        // can use this when none of the named ones match.
        // shell.c's dot-command names are alphanumeric+underscore
        // (see do_meta_command); we reflect that here. Allowing `-`
        // would collide with `--` line-comment opener after a
        // command name, breaking comment placement.
        alias(
          token(prec(-1, seq(".", /[a-zA-Z_][a-zA-Z0-9_]*/))),
          $.unknown_dot_command_name,
        ),
      ),
  },
});
