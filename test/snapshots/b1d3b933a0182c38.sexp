# input:
#   ALTER TABLE users ADD COLUMN email TEXT NOT NULL;
---
(source_file
  (alter_table_statement
    name: (qualified_table_name
      name: (identifier))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier))
      constraint: (column_constraint))))
