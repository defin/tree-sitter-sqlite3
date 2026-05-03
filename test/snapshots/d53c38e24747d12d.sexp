# input:
#   INSERT INTO users VALUES (1, 'alice'), (2, 'bob');
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    source: (values_clause
      value: (numeric_literal)
      value: (string_literal)
      value: (numeric_literal)
      value: (string_literal))))
