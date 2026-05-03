# input:
#   INSERT INTO users (id) VALUES (?);
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    columns: (column_name_list
      column: (identifier))
    source: (values_clause
      value: (bind_parameter))))
