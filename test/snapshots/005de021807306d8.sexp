# input:
#   ANALYZE main.users;
---
(source_file
  (analyze_statement
    target: (qualified_table_name
      schema: (identifier)
      name: (identifier))))
