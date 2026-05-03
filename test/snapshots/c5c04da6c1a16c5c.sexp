# input:
#   ALTER TABLE users RENAME TO accounts;
---
(source_file
  (alter_table_statement
    name: (qualified_table_name
      name: (identifier))
    new_name: (identifier)))
