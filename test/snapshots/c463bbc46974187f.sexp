# input:
#   CREATE TABLE orders (id INTEGER, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE);
---
(source_file
  (create_table_statement
    name: (qualified_table_name
      name: (identifier))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier)))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier))
      constraint: (column_constraint
        (foreign_key_clause
          table: (identifier)
          column: (identifier))))))
