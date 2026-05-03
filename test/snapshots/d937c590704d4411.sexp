# input:
#   UPDATE users SET name = 'a' ORDER BY id DESC LIMIT 10;
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (string_literal))
    order_by: (order_by_clause
      (order_term
        (column_reference
          name: (identifier))))
    limit: (limit_clause
      (numeric_literal))))
