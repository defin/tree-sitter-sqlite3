# input:
#   DROP INDEX IF EXISTS idx_user_name;
---
(source_file
  (drop_index_statement
    name: (qualified_table_name
      name: (identifier))))
