# input:
#   INSERT INTO main.users VALUES (1);
---
(source_file
  (insert_statement
    target: (qualified_table_name
      schema: (identifier)
      name: (identifier))
    source: (values_clause
      value: (numeric_literal))))
