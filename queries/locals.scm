; Local-symbol scopes for tree-sitter-sqlite3.
;
; sqlite SQL has very limited lexical scoping — only CTE names, table
; aliases, and column aliases. We mark CTE-and-WITH and SELECT-with-FROM
; as scopes so editors can resolve "go to definition" within those
; bounds.

; A SELECT statement opens a scope where its FROM aliases and CTE
; names are resolvable.
(select_statement) @local.scope

; CREATE VIEW body acts like a SELECT scope.
(create_view_statement) @local.scope

; CREATE TRIGGER body — each trigger statement runs in the trigger's
; own scope (NEW.x / OLD.x references).
(create_trigger_statement) @local.scope

; CTE name is a definition; references to it within the same WITH /
; following SELECT pick up via @local.reference on the table reference.
(cte_definition
  name: (identifier) @local.definition)

; Table aliases.
(table_or_subquery
  alias: (identifier) @local.definition)

; Column alias in a SELECT result column.
(expression_result_column
  alias: (identifier) @local.definition)

; Bind-parameter names are scoped to the statement.
(bind_parameter) @local.reference

; Table-name references resolve against the current scope's CTE and
; alias definitions.
(qualified_table_name
  name: (identifier) @local.reference)
