# input:
#   REPLACE INTO users VALUES (1);
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    source: (values_clause
      value: (numeric_literal))))
