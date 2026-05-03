# input:
#   INSERT INTO t (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    columns: (column_name_list
      column: (identifier))
    source: (values_clause
      value: (numeric_literal))
    upsert: (upsert_clause
      target_column: (indexed_column
        expression: (column_reference
          name: (identifier))))))
