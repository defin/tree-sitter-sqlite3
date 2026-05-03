# input:
#   INSERT INTO users DEFAULT VALUES;
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    source: (default_values_clause)))
