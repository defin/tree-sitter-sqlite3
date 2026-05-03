# input:
#   UPDATE users SET x = 1 LIMIT 10 OFFSET 5;
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (numeric_literal))
    limit: (limit_clause
      (numeric_literal)
      (numeric_literal))))
