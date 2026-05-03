; Symbol-tag captures for tree-sitter-sqlite3.
;
; Used by github.com/tree-sitter/tree-sitter for ctags-style symbol
; indexing — code search, outlines, "go to symbol".

; Tables defined via CREATE TABLE.
(create_table_statement
  name: (qualified_table_name
    name: (identifier) @name)) @definition.class

; Views.
(create_view_statement
  name: (qualified_table_name
    name: (identifier) @name)) @definition.class

; Indexes.
(create_index_statement
  name: (qualified_table_name
    name: (identifier) @name)) @definition.constant

; Triggers.
(create_trigger_statement
  name: (qualified_table_name
    name: (identifier) @name)) @definition.method

; Virtual tables.
(create_virtual_table_statement
  name: (qualified_table_name
    name: (identifier) @name)) @definition.class

; CTE names — local definitions inside a WITH clause.
(cte_definition
  name: (identifier) @name) @definition.constant
