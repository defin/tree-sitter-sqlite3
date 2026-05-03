# input:
#   DELETE FROM users;
---
(source_file
  (delete_statement
    target: (qualified_table_name
      name: (identifier))))
