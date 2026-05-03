; Highlights for tree-sitter-sqlite3.
;
; Capture names follow the tree-sitter highlight-capture convention so
; downstream consumers (Helix, Neovim, GitHub linguist, etc.) can map
; them to their colour schemes without per-language overrides.

; ---- Keywords ----------------------------------------------------------------

[
  "SELECT"
  "DISTINCT"
  "ALL"
  "FROM"
  "WHERE"
  "GROUP"
  "BY"
  "HAVING"
  "ORDER"
  "ASC"
  "DESC"
  "LIMIT"
  "OFFSET"
  "WINDOW"
  "OVER"
  "FILTER"
  "PARTITION"
  "RANGE"
  "ROWS"
  "GROUPS"
  "BETWEEN"
  "AND"
  "OR"
  "NOT"
  "IN"
  "EXISTS"
  "IS"
  "ISNULL"
  "NOTNULL"
  "NULL"
  "TRUE"
  "FALSE"
  "LIKE"
  "GLOB"
  "REGEXP"
  "MATCH"
  "ESCAPE"
  "COLLATE"
  "AS"
  "CASE"
  "WHEN"
  "THEN"
  "ELSE"
  "END"
  "CAST"
  "CURRENT"
  "PRECEDING"
  "FOLLOWING"
  "UNBOUNDED"
  "ROW"
  "EXCLUDE"
  "OTHERS"
  "TIES"
  "NO"
  "INSERT"
  "REPLACE"
  "INTO"
  "VALUES"
  "DEFAULT"
  "ON"
  "CONFLICT"
  "DO"
  "NOTHING"
  "UPDATE"
  "SET"
  "RETURNING"
  "DELETE"
  "INDEXED"
  "USING"
  "CREATE"
  "TABLE"
  "TEMP"
  "TEMPORARY"
  "IF"
  "INDEX"
  "UNIQUE"
  "VIEW"
  "TRIGGER"
  "BEFORE"
  "AFTER"
  "INSTEAD"
  "OF"
  "FOR"
  "EACH"
  "BEGIN"
  "VIRTUAL"
  "CONSTRAINT"
  "PRIMARY"
  "KEY"
  "AUTOINCREMENT"
  "CHECK"
  "REFERENCES"
  "GENERATED"
  "ALWAYS"
  "STORED"
  "DEFERRABLE"
  "DEFERRED"
  "IMMEDIATE"
  "EXCLUSIVE"
  "INITIALLY"
  "STRICT"
  "WITHOUT"
  "FOREIGN"
  "CASCADE"
  "RESTRICT"
  "ACTION"
  "ALTER"
  "RENAME"
  "TO"
  "ADD"
  "COLUMN"
  "DROP"
  "WITH"
  "RECURSIVE"
  "MATERIALIZED"
  "UNION"
  "INTERSECT"
  "EXCEPT"
  "JOIN"
  "INNER"
  "LEFT"
  "RIGHT"
  "FULL"
  "OUTER"
  "CROSS"
  "NATURAL"
  "ATTACH"
  "DETACH"
  "DATABASE"
  "PRAGMA"
  "VACUUM"
  "INTO"
  "REINDEX"
  "ANALYZE"
  "EXPLAIN"
  "QUERY"
  "PLAN"
  "TRANSACTION"
  "COMMIT"
  "ROLLBACK"
  "SAVEPOINT"
  "RELEASE"
  "ABORT"
  "FAIL"
  "IGNORE"
] @keyword

; ---- Literals ----------------------------------------------------------------

(numeric_literal) @number
(string_literal) @string
(blob_literal) @string.special
(null_literal) @constant.builtin
(true_literal) @constant.builtin.boolean
(false_literal) @constant.builtin.boolean
(current_time_literal) @constant.builtin
(bind_parameter) @variable.parameter

; ---- Operators ---------------------------------------------------------------

[
  "+"
  "-"
  "*"
  "/"
  "%"
  "="
  "=="
  "!="
  "<>"
  "<"
  "<="
  ">"
  ">="
  "&"
  "|"
  "<<"
  ">>"
  "||"
  "->"
  "->>"
  "~"
] @operator

; ---- Punctuation -------------------------------------------------------------

[
  "("
  ")"
] @punctuation.bracket

[
  ","
  ";"
  "."
] @punctuation.delimiter

; ---- Comments ----------------------------------------------------------------

(line_comment) @comment
(block_comment) @comment

; ---- Identifiers -------------------------------------------------------------

(quoted_identifier) @string.special.symbol

; Function calls take the @function highlight on the name.
(function_call name: (identifier) @function)

; CAST type names get @type.
(type_name (identifier) @type)

; CTE names are definitions.
(cte_definition name: (identifier) @variable.builtin)

; Column references — a 3-part schema.table.column gets each part
; highlighted distinctly.
(column_reference
  schema: (identifier) @namespace
  table: (identifier) @variable
  name: (identifier) @property)

(column_reference
  table: (identifier) @variable
  name: (identifier) @property)

(column_reference
  name: (identifier) @property)

; Table references in FROM / JOIN / INSERT INTO / UPDATE etc.
(qualified_table_name
  schema: (identifier) @namespace
  name: (identifier) @variable)

(qualified_table_name
  name: (identifier) @variable)

; Default identifier highlight — bare names that aren't otherwise
; classified (e.g. column-name positions in DDL, alias bindings).
(identifier) @variable

; ---- Dot-commands ------------------------------------------------------------

(dot_command) @function.builtin
