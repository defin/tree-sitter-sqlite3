# input:
#   DROP TABLE IF EXISTS users;
---
(source_file
  (drop_table_statement
    name: (qualified_table_name
      name: (identifier))))
