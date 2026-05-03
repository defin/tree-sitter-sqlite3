# input:
#   DROP TRIGGER IF EXISTS log_insert;
---
(source_file
  (drop_trigger_statement
    name: (qualified_table_name
      name: (identifier))))
