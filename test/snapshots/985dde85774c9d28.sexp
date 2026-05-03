# input:
#   INSERT INTO t (id, n) VALUES (1, 1) ON CONFLICT (id) DO UPDATE SET n = n + 1;
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
      value: (numeric_literal))
    upsert: (upsert_clause
      target_column: (indexed_column
        expression: (column_reference
          name: (identifier)))
      assignment: (set_assignment
        column: (identifier)
        value: (binary_expression
          left: (column_reference
            name: (identifier))
          right: (numeric_literal))))))
