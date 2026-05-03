# input:
#   CREATE TABLE t (id INTEGER, full_name TEXT GENERATED ALWAYS AS (id || 'x') STORED);
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
        (identifier))
      constraint: (column_constraint
        generated_expression: (binary_expression
          left: (column_reference
            name: (identifier))
          right: (string_literal))))))
