# input:
#   CREATE TABLE t (id INTEGER PRIMARY KEY) STRICT, WITHOUT ROWID;
---
(source_file
  (create_table_statement
    name: (qualified_table_name
      name: (identifier))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier))
      constraint: (column_constraint))
    options: (table_options
      option: (identifier))))
