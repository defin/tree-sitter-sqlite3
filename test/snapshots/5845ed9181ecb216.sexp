# input:
#   DELETE FROM users WHERE id > 0 ORDER BY id LIMIT 10;
---
(source_file
  (delete_statement
    target: (qualified_table_name
      name: (identifier))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))
    order_by: (order_by_clause
      (order_term
        (column_reference
          name: (identifier))))
    limit: (limit_clause
      (numeric_literal))))
