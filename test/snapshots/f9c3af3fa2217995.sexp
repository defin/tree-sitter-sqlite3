# input:
#   UPDATE OR REPLACE users SET name = 'alice';
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (string_literal))))
