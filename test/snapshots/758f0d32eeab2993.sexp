# input:
#   insert into Users values (1, 'alice');
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    source: (values_clause
      value: (numeric_literal)
      value: (string_literal))))
