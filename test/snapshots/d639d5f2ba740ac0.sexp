# input:
#   INSERT INTO t (n) VALUES (1) RETURNING id, n;
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    columns: (column_name_list
      column: (identifier))
    source: (values_clause
      value: (numeric_literal))
    returning: (returning_clause
      (result_column_list
        (expression_result_column
          expression: (column_reference
            name: (identifier)))
        (expression_result_column
          expression: (column_reference
            name: (identifier)))))))
