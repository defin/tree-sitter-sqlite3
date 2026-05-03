# input:
#   ALTER TABLE users DROP COLUMN unused;
---
(source_file
  (alter_table_statement
    name: (qualified_table_name
      name: (identifier))
    dropped_column: (identifier)))
