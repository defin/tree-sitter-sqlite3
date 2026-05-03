# input:
#   UPDATE users SET name = 'alice' WHERE id = 1;
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (string_literal))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))))
