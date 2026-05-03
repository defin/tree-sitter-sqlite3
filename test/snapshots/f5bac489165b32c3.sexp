# input:
#   CREATE INDEX idx_user_name ON users (name);
---
(source_file
  (create_index_statement
    name: (qualified_table_name
      name: (identifier))
    table: (identifier)
    column: (indexed_column
      expression: (column_reference
        name: (identifier)))))
