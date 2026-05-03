# input:
#   CREATE TEMP VIEW IF NOT EXISTS v (a, b) AS SELECT 1, 2;
---
(source_file
  (create_view_statement
    name: (qualified_table_name
      name: (identifier))
    column: (identifier)
    column: (identifier)
    body: (select_clause
      columns: (result_column_list
        (expression_result_column
          expression: (numeric_literal))
        (expression_result_column
          expression: (numeric_literal))))))
