# input:
#   UPDATE users SET name = 'alice', age = 30;
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (string_literal))
    assignment: (set_assignment
      column: (identifier)
      value: (numeric_literal))))
