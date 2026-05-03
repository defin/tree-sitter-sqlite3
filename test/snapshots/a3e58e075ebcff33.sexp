# input:
#   UPDATE main.users SET name = 'a' WHERE id = 1;
---
(source_file
  (update_statement
    target: (qualified_table_name
      schema: (identifier)
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (string_literal))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))))
