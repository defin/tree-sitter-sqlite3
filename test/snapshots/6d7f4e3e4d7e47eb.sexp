# input:
#   CREATE TABLE t (
#     a INTEGER,
#     b INTEGER,
#     PRIMARY KEY (a, b),
#     UNIQUE (b),
#     FOREIGN KEY (a) REFERENCES other(id)
#   );
---
(source_file
  (create_table_statement
    name: (qualified_table_name
      name: (identifier))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier)))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier)))
    constraint: (table_constraint
      column: (indexed_column
        expression: (column_reference
          name: (identifier)))
      column: (indexed_column
        expression: (column_reference
          name: (identifier))))
    constraint: (table_constraint
      column: (indexed_column
        expression: (column_reference
          name: (identifier))))
    constraint: (table_constraint
      column: (identifier)
      (foreign_key_clause
        table: (identifier)
        column: (identifier)))))
