# input:
#   CREATE UNIQUE INDEX idx_email ON users (email) WHERE email IS NOT NULL;
---
(source_file
  (create_index_statement
    name: (qualified_table_name
      name: (identifier))
    table: (identifier)
    column: (indexed_column
      expression: (column_reference
        name: (identifier)))
    where: (where_clause
      (is_expression
        left: (column_reference
          name: (identifier))
        right: (unary_expression
          operand: (null_literal))))))
