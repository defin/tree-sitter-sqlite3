# input:
#   INSERT INTO users (id, name) VALUES (1, 'alice');
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    columns: (column_name_list
      column: (identifier)
      column: (identifier))
    source: (values_clause
      value: (numeric_literal)
      value: (string_literal))))
