# input:
#   UPDATE users INDEXED BY idx_name SET x = 1;
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    (identifier)
    assignment: (set_assignment
      column: (identifier)
      value: (numeric_literal))))
