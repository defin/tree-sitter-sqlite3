# input:
#   DELETE FROM users INDEXED BY idx_id WHERE id = 1;
---
(source_file
  (delete_statement
    target: (qualified_table_name
      name: (identifier))
    (identifier)
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))))
