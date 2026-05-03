# input:
#   CREATE TABLE users (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL UNIQUE,
#     email TEXT DEFAULT 'unknown',
#     age INTEGER CHECK (age > 0)
#   );
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
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier))
      constraint: (column_constraint)
      constraint: (column_constraint))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier))
      constraint: (column_constraint
        default: (string_literal)))
    column: (column_definition
      name: (identifier)
      type: (type_name
        (identifier))
      constraint: (column_constraint
        check: (binary_expression
          left: (column_reference
            name: (identifier))
          right: (numeric_literal))))))
