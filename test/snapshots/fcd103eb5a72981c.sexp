# input:
#   CREATE TABLE IF NOT EXISTS main.t (id INTEGER);
---
(source_file
  (create_table_statement
    name: (qualified_table_name
      schema: (identifier)
      name: (identifier))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier)))))
