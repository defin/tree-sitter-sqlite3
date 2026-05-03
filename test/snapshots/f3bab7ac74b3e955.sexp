# input:
#   SELECT id AS user_id FROM users;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (column_reference
          name: (identifier))
        alias: (identifier)))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
