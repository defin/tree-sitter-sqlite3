# input:
#   CREATE INDEX idx ON t (a ASC, b DESC);
---
(source_file
  (create_index_statement
    name: (qualified_table_name
      name: (identifier))
    table: (identifier)
    column: (indexed_column
      expression: (column_reference
        name: (identifier)))
    column: (indexed_column
      expression: (column_reference
        name: (identifier)))))
