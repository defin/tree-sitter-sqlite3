# input:
#   ALTER TABLE users RENAME COLUMN name TO full_name;
---
(source_file
  (alter_table_statement
    name: (qualified_table_name
      name: (identifier))
    old_column: (identifier)
    new_column: (identifier)))
