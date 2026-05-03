# input:
#   DELETE FROM users LIMIT 5 OFFSET 10;
---
(source_file
  (delete_statement
    target: (qualified_table_name
      name: (identifier))
    limit: (limit_clause
      (numeric_literal)
      (numeric_literal))))
